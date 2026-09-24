"""États de paie Excel (F2, F13, D-49 à D-53) : livre de paie et état des charges, virements, billetage.

Les états lisent les bulletins validés ou payés, leurs lignes stockées et leurs champs figés (F7) ;
le rendu passe par ``XlsxRenderer`` (valeurs seulement, jamais de formules).
"""

import base64
from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..lib.ga_fiscal_core.cash_breakdown import cash_breakdown
from ..report.xlsx_renderer import XlsxRenderer

VALIDATED_STATES = ('validated', 'paid')  # sprint 0 point 3
NET_PAY_CODE = 'GA_NET_PAY'
NET_CODE = 'NET'
CHARGE_CATEGORIES = ('GA_SOC', 'GA_TAX', 'GA_EMPLOYER')  # retenues fiscales et sociales, charges patronales
EMPLOYER_CATEGORY = 'GA_EMPLOYER'


class L10nGaPayrollReport(models.TransientModel):
    _name = 'l10n_ga.payroll.report'
    _description = 'États de paie (Gabon)'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Lot de paie', check_company=True)
    date_from = fields.Date(string='Du', default=lambda self: date.today().replace(day=1))
    date_to = fields.Date(
        string='Au', default=lambda self: date.today().replace(day=1) + relativedelta(months=1, days=-1)
    )
    report_type = fields.Selection(
        [
            ('book', 'Livre de paie et état des charges'),
            ('transfer', 'Virements par banque'),
            ('cash', 'Billetage des paies en espèces'),
        ],
        string='État',
        required=True,
        default='book',
    )
    file = fields.Binary(string='Fichier', readonly=True, attachment=False)
    filename = fields.Char(readonly=True)

    @api.constrains('date_from', 'date_to', 'payslip_run_id')
    def _check_period(self):
        for wizard in self:
            if not wizard.payslip_run_id and not (wizard.date_from and wizard.date_to):
                raise ValidationError(self.env._('Choisissez un lot de paie ou une période.'))
            if not wizard.payslip_run_id and wizard.date_from > wizard.date_to:
                raise ValidationError(self.env._('La période se termine avant de commencer.'))

    # --- sélection (D-49) ------------------------------------------------------------------------

    def _slips(self):
        """Bulletins Gabon validés ou payés du lot, ou dont la date de fin tombe dans la période."""
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id), ('state', 'in', VALIDATED_STATES)]
        if self.payslip_run_id:
            domain.append(('payslip_run_id', '=', self.payslip_run_id.id))
        else:
            domain += [('date_to', '>=', self.date_from), ('date_to', '<=', self.date_to)]
        slips = self.env['hr.payslip'].search(domain)
        return slips.filtered('l10n_ga_is_ga').sorted(lambda s: (s.l10n_ga_employee_name or '', s.date_to, s.id))

    @staticmethod
    def _totals(slip):
        totals = defaultdict(float)
        for line in slip.line_ids:
            totals[line.code] += line.total
        return totals

    def _net_pay(self, slip):
        totals = self._totals(slip)
        return totals.get(NET_PAY_CODE, totals.get(NET_CODE, 0.0))

    def _identity(self, slip):
        return [slip.l10n_ga_registration_number or '', slip.l10n_ga_employee_name or slip.employee_id.name]

    # --- livre de paie et état des charges (F13) ---------------------------------------------------

    def _book_columns(self, slips):
        """Rubriques ayant au moins un montant sur la sélection, dans l'ordre des séquences (D-50)."""
        rules = {}
        for line in slips.line_ids.filtered('total'):
            rules.setdefault(line.code, line.salary_rule_id)
        return sorted(rules.items(), key=lambda item: (item[1].sequence, item[0]))

    def _render_book(self, renderer, slips):
        columns = self._book_columns(slips)
        codes = [code for code, _rule in columns]
        headers = [
            self.env._('Matricule'),
            self.env._('Salarié'),
            self.env._('Période'),
            self.env._('Parts'),
            *[f'{code} — {rule.name}' for code, rule in columns],
        ]
        rows = []
        sums = defaultdict(float)
        for slip in slips:
            totals = self._totals(slip)
            for code in codes:
                sums[code] += totals.get(code, 0.0)
            rows.append(
                [
                    *self._identity(slip),
                    f'{slip.date_to:%m/%Y}',
                    slip.l10n_ga_tax_parts_used,
                    *[totals.get(code, 0.0) for code in codes],
                ]
            )
        total_row = [self.env._('Total'), '', '', '', *[sums[code] for code in codes]]
        renderer.add_sheet(self.env._('Livre de paie'), headers, rows, totals=[total_row])
        self._render_charges(renderer, slips)

    @staticmethod
    def _root_category(rule):
        category = rule.category_id
        while category and category.code not in CHARGE_CATEGORIES:
            category = category.parent_id
        return category

    def _charge_rows(self, slips):
        """Par catégorie : (catégorie, [(code, libellé, part salariale, part patronale)])."""
        groups = defaultdict(dict)
        for line in slips.line_ids.filtered('total'):
            category = self._root_category(line.salary_rule_id)
            if not category:
                continue
            employee_part, employer_part, _name = groups[category].get(line.code, (0.0, 0.0, line.name))
            if category.code == EMPLOYER_CATEGORY:
                employer_part += line.total
            else:
                employee_part -= line.total  # retenue : ligne négative
            groups[category][line.code] = (employee_part, employer_part, line.salary_rule_id.name)
        ordered = sorted(groups.items(), key=lambda item: CHARGE_CATEGORIES.index(item[0].code))
        return [
            (category, [(code, *values[2:], *values[:2]) for code, values in sorted(rows.items())])
            for category, rows in ordered
        ]

    def _render_charges(self, renderer, slips):
        headers = [
            self.env._('Code'),
            self.env._('Rubrique'),
            self.env._('Part salariale'),
            self.env._('Part patronale'),
            self.env._('Total'),
        ]
        rows = []
        grand = [0.0, 0.0]
        for category, lines in self._charge_rows(slips):
            subtotal = [0.0, 0.0]
            for code, name, employee_part, employer_part in lines:
                rows.append([code, name, employee_part, employer_part, employee_part + employer_part])
                subtotal[0] += employee_part
                subtotal[1] += employer_part
            rows.append(['', self.env._('Sous-total %(category)s', category=category.name), *subtotal, sum(subtotal)])
            grand = [grand[0] + subtotal[0], grand[1] + subtotal[1]]
        renderer.add_sheet(
            self.env._('État des charges'), headers, rows, totals=[[self.env._('Total'), '', *grand, sum(grand)]]
        )

    # --- virements (F2) ----------------------------------------------------------------------------

    def _transfer_groups(self, slips):
        """Feuille → bulletins : une par banque (compte figé), « Chèques », « Sans compte » (D-52)."""
        groups = defaultdict(lambda: self.env['hr.payslip'])
        for slip in slips:
            if slip.l10n_ga_payment_mode == 'check':
                groups[self.env._('Chèques')] |= slip
            elif slip.l10n_ga_payment_mode == 'transfer':
                if slip.l10n_ga_bank_account:
                    groups[slip.l10n_ga_bank_name or self.env._('Banque non renseignée')] |= slip
                else:
                    groups[self.env._('Sans compte')] |= slip
        return dict(sorted(groups.items()))

    def _render_transfer(self, renderer, slips):
        headers = [
            self.env._('Matricule'),
            self.env._('Salarié'),
            self.env._('Banque'),
            self.env._('Compte'),
            self.env._('Net à payer'),
        ]
        groups = self._transfer_groups(slips)
        if not groups:
            renderer.add_sheet(self.env._('Virements'), headers, [])
        for name, group in groups.items():
            rows = [
                [
                    *self._identity(slip),
                    slip.l10n_ga_bank_name or '',
                    slip.l10n_ga_bank_account or '',
                    self._net_pay(slip),
                ]
                for slip in group
            ]
            total = sum(row[-1] for row in rows)
            renderer.add_sheet(name, headers, rows, totals=[[self.env._('Total'), '', '', '', total]])

    # --- billetage (F2) ----------------------------------------------------------------------------

    def _cash_rows(self, slips):
        """(coupures, [(bulletin, net à payer, Breakdown)]) des paies en espèces."""
        entries = []
        denominations = set()
        for slip in slips.filtered(lambda s: s.l10n_ga_payment_mode == 'cash'):
            params = slip.company_id._l10n_ga_fiscal_params(slip.date_to, raise_if_not_found=True)
            amount = self._net_pay(slip)
            breakdown = cash_breakdown(max(amount, 0), params.cash_denominations)
            denominations.update(value for value, _count in breakdown.counts)
            entries.append((slip, amount, breakdown))
        return sorted(denominations, reverse=True), entries

    def _render_cash(self, renderer, slips):
        denominations, entries = self._cash_rows(slips)
        headers = [
            self.env._('Matricule'),
            self.env._('Salarié'),
            self.env._('Net à payer'),
            *[str(value) for value in denominations],
            self.env._('Reste (pièces)'),
        ]
        rows = []
        counts = defaultdict(int)
        remainder = 0
        paid = 0.0
        for slip, amount, breakdown in entries:
            by_value = dict(breakdown.counts)
            for value in denominations:
                counts[value] += by_value.get(value, 0)
            remainder += breakdown.remainder
            paid += amount
            rows.append(
                [*self._identity(slip), amount, *[by_value.get(v, 0) for v in denominations], breakdown.remainder]
            )
        totals = [
            [self.env._('Nombre de coupures'), '', paid, *[counts[v] for v in denominations], remainder],
            [self.env._('Montant par coupure'), '', paid, *[counts[v] * v for v in denominations], remainder],
        ]
        renderer.add_sheet(self.env._('Billetage'), headers, rows, totals=totals)

    # --- génération ----------------------------------------------------------------------------------

    def _render(self):
        self.ensure_one()
        slips = self._slips()
        if not slips:
            raise UserError(self.env._('Aucun bulletin validé ou payé pour cette sélection.'))
        renderer = XlsxRenderer()
        {'book': self._render_book, 'transfer': self._render_transfer, 'cash': self._render_cash}[self.report_type](
            renderer, slips
        )
        return renderer.build()

    def _filename(self):
        label = {'book': 'livre_de_paie', 'transfer': 'virements', 'cash': 'billetage'}[self.report_type]
        scope = self.payslip_run_id.name or f'{self.date_from}_{self.date_to}'
        return f'{label}_{scope}.xlsx'.replace('/', '-').replace(' ', '_')

    def action_generate(self):
        self.ensure_one()
        self.write({'file': base64.b64encode(self._render()), 'filename': self._filename()})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': self.env._('États de paie'),
        }
