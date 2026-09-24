"""Prêts salariés (F1, RG19-RG21) : échéancier, octroi par spécifications (patron 12), cycle de vie (patron 7).

L'entrée de bulletin ``GA_LOAN`` est créée par les échéances sur le bulletin brouillon
(``hr.payslip._l10n_ga_loan_inputs``, sprint 0 point 6) ; l'échéance passe « retenue » à la
validation du bulletin (D-30). Les seuils d'octroi sont des paramètres datés (D-37).
"""

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..lib.ga_fiscal_core.labour import completed_years
from ..lib.ga_fiscal_core.loans import (
    LoanFacts,
    MaxInstallmentRatio,
    MaxOutstanding,
    MinSeniority,
    eligibility_failures,
    schedule,
)

VALIDATED_STATES = ('validated', 'paid')
ACTIVE_STATES = ('approved', 'running')
TO_PAY = 'to_pay'
SETTLED_LINE_STATES = ('withheld', 'repaid')


class L10nGaEmployeeLoan(models.Model):
    _name = 'l10n_ga.employee.loan'
    _description = 'Prêt salarié (Gabon)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Référence', required=True, readonly=True, copy=False, default='/')
    employee_id = fields.Many2one(
        'hr.employee', string='Salarié', required=True, tracking=True, check_company=True, index=True
    )
    company_id = fields.Many2one(
        'res.company', string='Société', required=True, default=lambda self: self.env.company, index=True
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    date = fields.Date(string='Date d’octroi', required=True, default=fields.Date.context_today, tracking=True)
    amount = fields.Monetary(string='Montant', required=True, tracking=True)
    installment_count = fields.Integer(string='Nombre d’échéances', required=True, default=1, tracking=True)
    first_due_date = fields.Date(
        string='Première échéance',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1) + relativedelta(months=1),
        tracking=True,
    )
    installment_amount = fields.Monetary(string='Mensualité', compute='_compute_installment_amount')
    state = fields.Selection(
        [
            ('draft', 'Brouillon'),
            ('approved', 'Approuvé'),
            ('running', 'En cours'),
            ('paid', 'Soldé'),
            ('cancelled', 'Annulé'),
        ],
        string='État',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    derogation = fields.Boolean(string='Dérogation RH', tracking=True, copy=False)
    derogation_reason = fields.Text(string='Motif de la dérogation', tracking=True, copy=False)
    derogation_user_id = fields.Many2one('res.users', string='Dérogation accordée par', readonly=True, copy=False)
    derogation_date = fields.Datetime(string='Dérogation accordée le', readonly=True, copy=False)
    eligibility_issues = fields.Text(string='Conditions non remplies', compute='_compute_eligibility_issues')
    line_ids = fields.One2many('l10n_ga.employee.loan.line', 'loan_id', string='Échéancier', copy=False)
    remaining_amount = fields.Monetary(string='Restant dû', compute='_compute_amounts', store=True)
    withheld_amount = fields.Monetary(string='Remboursé', compute='_compute_amounts', store=True)
    note = fields.Text(string='Notes')

    _amount_positive = models.Constraint('CHECK (amount > 0)', 'Le montant du prêt doit être strictement positif.')
    _installment_count_positive = models.Constraint(
        'CHECK (installment_count > 0)', 'Le nombre d’échéances doit être strictement positif.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('l10n_ga.employee.loan') or '/'
        return super().create(vals_list)

    @api.depends('line_ids.amount', 'amount', 'installment_count')
    def _compute_installment_amount(self):
        for loan in self:
            amounts = loan.line_ids.mapped('amount')
            loan.installment_amount = max(amounts) if amounts else loan.amount / (loan.installment_count or 1)

    @api.depends('line_ids.amount', 'line_ids.state')
    def _compute_amounts(self):
        for loan in self:
            loan.remaining_amount = sum(loan.line_ids.filtered(lambda line: line.state == TO_PAY).mapped('amount'))
            loan.withheld_amount = sum(
                loan.line_ids.filtered(lambda line: line.state in SETTLED_LINE_STATES).mapped('amount')
            )

    @api.constrains('derogation', 'derogation_reason')
    def _check_derogation_reason(self):
        for loan in self:
            if loan.derogation and not (loan.derogation_reason or '').strip():
                raise ValidationError(self.env._('Une dérogation RH doit être motivée (prêt %s).', loan.name))

    # --- échéancier ----------------------------------------------------------------------------

    def action_compute_schedule(self):
        for loan in self:
            if loan.state != 'draft':
                raise UserError(self.env._('L’échéancier ne se recalcule qu’en brouillon (prêt %s).', loan.name))
            loan.line_ids.unlink()
            loan.write(
                {
                    'line_ids': [
                        fields.Command.create(
                            {'due_date': loan.first_due_date + relativedelta(months=index), 'amount': amount}
                        )
                        for index, amount in enumerate(schedule(loan.amount, loan.installment_count))
                    ]
                }
            )
        return True

    def _next_free_due_date(self):
        """Premier mois après la dernière échéance (report, D-34)."""
        self.ensure_one()
        return max(self.line_ids.mapped('due_date')) + relativedelta(months=1)

    def _reduce_from_end(self, amount, keep=None):
        """Réduit les échéances « à payer » en partant de la dernière (remboursement anticipé, D-33)."""
        self.ensure_one()
        lines = self.line_ids.filtered(lambda line: line.state == TO_PAY and line != keep and not line.payslip_id)
        for line in lines.sorted(lambda line: (line.due_date, line.id), reverse=True):
            if amount <= 0:
                break
            if line.amount <= amount:
                amount -= line.amount
                line.unlink()
            else:
                line.amount -= amount
                amount = 0

    # --- octroi (patron 12, RG20) --------------------------------------------------------------

    def _param(self, code):
        return self.env['hr.rule.parameter']._get_parameter_from_code(code, self.date)

    def _reference_net(self):
        """NET du dernier bulletin validé à la date d'octroi (D-31) ; 0 sans bulletin."""
        self.ensure_one()
        slip = self.env['hr.payslip'].search(
            [
                ('employee_id', '=', self.employee_id.id),
                ('company_id', '=', self.company_id.id),
                ('state', 'in', VALIDATED_STATES),
                ('date_to', '<=', self.date),
            ],
            order='date_to desc, id desc',
            limit=1,
        )
        return sum(slip.line_ids.filtered(lambda line: line.code == 'NET').mapped('total'))

    def _outstanding(self):
        self.ensure_one()
        others = self.search(
            [('employee_id', '=', self.employee_id.id), ('state', 'in', ACTIVE_STATES), ('id', '!=', self.id)]
        )
        return sum(others.mapped('remaining_amount'))

    def _eligibility_facts(self):
        self.ensure_one()
        version = self.employee_id._get_version(self.date)
        return LoanFacts(
            seniority_years=completed_years(version._l10n_ga_seniority_start(), self.date),
            installment=self.installment_amount,
            reference_net=self._reference_net(),
            outstanding=self._outstanding(),
            amount=self.amount,
        )

    def _eligibility_spec(self):
        return (
            MinSeniority(self._param('l10n_ga_loan_min_seniority_years'))
            & MaxInstallmentRatio(self._param('l10n_ga_loan_max_installment_ratio'))
            & MaxOutstanding(self.company_id.l10n_ga_loan_outstanding_cap)
        )

    def _failure_message(self, failure):
        if failure.code == 'seniority':
            return self.env._(
                'Ancienneté de %(actual)s an(s), inférieure au minimum de %(limit)s ans.',
                actual=failure.actual,
                limit=failure.limit,
            )
        if failure.code == 'installment':
            return self.env._(
                'Mensualité %(actual)s supérieure à la part autorisée du net (%(limit)s).',
                actual=failure.actual,
                limit=failure.limit,
            )
        return self.env._(
            'Encours %(actual)s supérieur au plafond de la société (%(limit)s).',
            actual=failure.actual,
            limit=failure.limit,
        )

    def _eligibility_messages(self):
        self.ensure_one()
        return [
            self._failure_message(f) for f in eligibility_failures(self._eligibility_spec(), self._eligibility_facts())
        ]

    @api.depends('employee_id', 'date', 'amount', 'installment_count', 'line_ids.amount', 'company_id')
    def _compute_eligibility_issues(self):
        for loan in self:
            messages = loan._eligibility_messages() if loan.employee_id and loan.amount > 0 and loan.date else []
            loan.eligibility_issues = '\n'.join(messages)

    # --- cycle de vie (patron 7) ---------------------------------------------------------------

    def action_approve(self):
        if not self.env.su and not self.env.user.has_group('hr_payroll.group_hr_payroll_manager'):
            raise UserError(self.env._('Seul un responsable de la paie approuve un prêt.'))
        for loan in self:
            if loan.state != 'draft':
                raise UserError(self.env._('Seul un prêt en brouillon peut être approuvé (%s).', loan.name))
            if not loan.line_ids:
                loan.action_compute_schedule()
            if abs(sum(loan.line_ids.mapped('amount')) - loan.amount) >= 1:
                raise UserError(self.env._('L’échéancier ne correspond pas au montant du prêt %s.', loan.name))
            messages = loan._eligibility_messages()
            if messages and not loan.derogation:
                raise UserError('\n'.join([self.env._('Prêt %s refusé :', loan.name), *messages]))
            values = {'state': 'approved'}
            if messages:
                values.update(derogation_user_id=self.env.user.id, derogation_date=fields.Datetime.now())
                loan.message_post(
                    body=self.env._(
                        'Dérogation RH : %(reason)s — conditions levées : %(issues)s',
                        reason=loan.derogation_reason,
                        issues=' ; '.join(messages),
                    )
                )
            loan.write(values)
        return True

    def action_cancel(self):
        for loan in self:
            if loan.line_ids.filtered(lambda line: line.state in SETTLED_LINE_STATES or line.payslip_id):
                raise UserError(self.env._('Le prêt %s a déjà des échéances retenues : annulation refusée.', loan.name))
        self.write({'state': 'cancelled'})
        return True

    def action_draft(self):
        for loan in self:
            if loan.state not in ('approved', 'cancelled') or loan.line_ids.filtered('payslip_id'):
                raise UserError(self.env._('Le prêt %s ne peut pas revenir en brouillon.', loan.name))
        self.write({'state': 'draft', 'derogation_user_id': False, 'derogation_date': False})
        return True

    def _update_state(self):
        """Approuvé → en cours à la première échéance réglée → soldé quand plus rien n'est dû."""
        for loan in self.filtered(lambda loan: loan.state in (*ACTIVE_STATES, 'paid')):
            if not loan.line_ids.filtered(lambda line: line.state == TO_PAY):
                state = 'paid'
            elif loan.line_ids.filtered(lambda line: line.state in SETTLED_LINE_STATES):
                state = 'running'
            else:
                state = 'approved'
            if loan.state != state:
                loan.state = state

    def action_early_repayment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Remboursement anticipé'),
            'res_model': 'l10n_ga.loan.early.repayment',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_loan_id': self.id},
        }


class L10nGaEmployeeLoanLine(models.Model):
    _name = 'l10n_ga.employee.loan.line'
    _description = 'Échéance de prêt salarié (Gabon)'
    _order = 'due_date, id'
    _check_company_auto = True

    loan_id = fields.Many2one('l10n_ga.employee.loan', string='Prêt', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='loan_id.company_id', store=True, index=True)
    employee_id = fields.Many2one(related='loan_id.employee_id', store=True, index=True)
    currency_id = fields.Many2one(related='loan_id.currency_id')
    due_date = fields.Date(string='Échéance', required=True)
    amount = fields.Monetary(string='Montant', required=True)
    state = fields.Selection(
        [
            (TO_PAY, 'À payer'),
            ('withheld', 'Retenue'),
            ('postponed', 'Reportée'),
            ('repaid', 'Remboursée hors paie'),
        ],
        string='État',
        default=TO_PAY,
        required=True,
    )
    # RG21 : une échéance est retenue par au plus un bulletin.
    payslip_id = fields.Many2one('hr.payslip', string='Bulletin', readonly=True, copy=False, check_company=True)
    note = fields.Char()

    _amount_positive = models.Constraint('CHECK (amount > 0)', 'Le montant d’une échéance doit être positif.')

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_settled(self):
        if self.filtered(lambda line: line.state != TO_PAY or line.payslip_id):
            raise UserError(self.env._('Une échéance retenue, reportée ou remboursée ne peut pas être supprimée.'))

    def action_postpone(self):
        """Report (D-34) : l'échéance est reportée, une échéance de même montant est ajoutée en fin."""
        for line in self:
            if line.state != TO_PAY or line.payslip_id or line.loan_id.state not in ACTIVE_STATES:
                raise UserError(self.env._('Seule une échéance à payer d’un prêt approuvé peut être reportée.'))
            due = line.loan_id._next_free_due_date()
            self.create({'loan_id': line.loan_id.id, 'due_date': due, 'amount': line.amount})
            line.write({'state': 'postponed', 'note': self.env._('Reportée au %s', due)})
            line.loan_id.message_post(
                body=self.env._('Échéance du %(date)s reportée au %(due)s.', date=line.due_date, due=due)
            )
        return True
