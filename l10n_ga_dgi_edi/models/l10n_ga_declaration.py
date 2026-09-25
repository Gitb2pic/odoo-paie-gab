import base64
import hashlib
import json
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from markupsafe import Markup  # pylint: disable=import-error

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round

from ..renderers.xlsm_template import XlsmTemplateRenderer
from ..renderers.xlsx_builder import XlsxDeclarationBuilder
from ..renderers.xlsx_html import workbook_to_html
from .checks import BLOCKING, run_checks
from .l10n_ga_declaration_frozen_mixin import FROZEN_STATES
from .l10n_ga_declaration_type import PERIOD_MONTHS

STATES = [
    ('draft', 'Brouillon'),
    ('computed', 'Calculée'),
    ('validated', 'Validée'),
    ('filed', 'Déposée'),
    ('paid', 'Payée'),
    ('cancel', 'Annulée'),
]
# Champs de l'instantané : non modifiables une fois la déclaration validée (RG14).
FROZEN_FIELDS = {'company_id', 'type_id', 'date_from', 'date_to', 'rectified_id', 'sha256', 'amount_total'}
ENGINE = 'l10n_ga_declaration_engine'
DECLARANT_GROUP = 'l10n_ga_dgi_edi.group_l10n_ga_declarant'
ACTIVITY_DUE = 'l10n_ga_dgi_edi.mail_activity_type_declaration_due'
ACTIVITY_FIX = 'l10n_ga_dgi_edi.mail_activity_type_declaration_fix'
OVERPAID = 'GA_DECL_OVERPAID'
AMOUNT_FORMAT = '#,##0'


class L10nGaDeclaration(models.Model):
    """Déclaration fiscale ou sociale (ADR-06, ADR-07).

    Patrons : Template Method (``action_compute``), State (``_TRANSITIONS``), Snapshot
    (``_snapshot`` à la validation : valeurs stockées, fichiers joints, empreinte SHA-256),
    Observer (validation des bulletins, cron des échéances).
    """

    _name = 'l10n_ga.declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Déclaration fiscale ou sociale (Gabon)'
    _order = 'date_from desc, type_id, id desc'
    _check_company_auto = True

    _TRANSITIONS = {
        'draft': {'computed', 'cancel'},
        'computed': {'computed', 'draft', 'validated', 'cancel'},
        'validated': {'computed', 'filed'},
        'filed': {'paid'},
        'paid': set(),
        'cancel': {'draft'},
    }

    name = fields.Char(string='Référence', compute='_compute_name', store=True)
    company_id = fields.Many2one(
        'res.company', string='Société', required=True, default=lambda self: self.env.company, index=True
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    type_id = fields.Many2one('l10n_ga.declaration.type', string='Imprimé', required=True, ondelete='restrict')
    type_code = fields.Char(related='type_id.code', string='Code imprimé')
    authority = fields.Selection(related='type_id.authority')
    date_from = fields.Date(string='Du', required=True)
    date_to = fields.Date(string='Au', required=True)
    due_date = fields.Date(
        string='Échéance', compute='_compute_due_date', store=True, readonly=False, tracking=True, index=True
    )
    state = fields.Selection(STATES, string='État', default='draft', required=True, readonly=True, tracking=True)
    amount_total = fields.Monetary(string='Total dû', compute='_compute_amount_total', store=True)
    line_ids = fields.One2many('l10n_ga.declaration.line', 'declaration_id', string='Cases')
    detail_ids = fields.One2many('l10n_ga.declaration.detail', 'declaration_id', string='Détails')
    issue_ids = fields.One2many('l10n_ga.check.issue', 'declaration_id', string='Anomalies')
    blocking_count = fields.Integer(string='Anomalies bloquantes', compute='_compute_issue_counts')
    warning_count = fields.Integer(string='Avertissements', compute='_compute_issue_counts')
    payment_ids = fields.One2many('l10n_ga.declaration.payment', 'declaration_id', string='Quittances')
    amount_paid = fields.Monetary(string='Versé', compute='_compute_amount_paid', store=True)
    amount_residual = fields.Monetary(string='Reste à payer', compute='_compute_amount_paid', store=True)
    rectified_id = fields.Many2one(
        'l10n_ga.declaration',
        string='Rectifie',
        readonly=True,
        ondelete='restrict',
        check_company=True,
        index='btree_not_null',
    )
    rectification_ids = fields.One2many('l10n_ga.declaration', 'rectified_id', string='Rectificatives')
    filing_date = fields.Date(string='Déposée le', tracking=True, copy=False)
    filing_number = fields.Char(string='N° de dépôt', tracking=True, copy=False)
    validated_date = fields.Datetime(string='Validée le', readonly=True, copy=False)
    validated_by_id = fields.Many2one('res.users', string='Validée par', readonly=True, copy=False)
    sha256 = fields.Char(string='Empreinte SHA-256', readonly=True, copy=False)
    snapshot_attachment_ids = fields.Many2many(
        'ir.attachment',
        'l10n_ga_declaration_snapshot_attachment_rel',
        'declaration_id',
        'attachment_id',
        string='Fichiers figés',
        readonly=True,
        copy=False,
    )

    _dates_check = models.Constraint('CHECK (date_to >= date_from)', 'La fin de période doit suivre son début.')
    # RG11 : une seule déclaration non rectificative active par (société, type, période) (D-65).
    _period_unique = models.UniqueIndex(
        "(company_id, type_id, date_from, date_to) WHERE rectified_id IS NULL AND state != 'cancel'",
        'Une déclaration de ce type existe déjà pour cette société et cette période ; créez une rectificative.',
    )

    # --- champs calculés ----------------------------------------------------------------------

    @api.depends('type_id.code', 'type_id.periodicity', 'date_from', 'date_to', 'rectified_id')
    def _compute_name(self):
        for decl in self:
            if not (decl.type_id and decl.date_from):
                decl.name = self.env._('Nouvelle déclaration')
                continue
            months = PERIOD_MONTHS[decl.type_id.periodicity]
            if months == PERIOD_MONTHS['yearly']:
                period = f'{decl.date_from:%Y}'
            elif months == PERIOD_MONTHS['quarterly']:
                period = f'T{(decl.date_from.month - 1) // months + 1} {decl.date_from:%Y}'
            else:
                period = f'{decl.date_from:%m/%Y}'
            name = f'{decl.type_id.code} {period}'
            if decl.rectified_id:
                name = self.env._('%(name)s (rectificative)', name=name)
            decl.name = name

    @api.depends('type_id.due_months', 'type_id.due_day', 'date_to')
    def _compute_due_date(self):
        for decl in self:
            decl.due_date = decl.type_id._due_date(decl.date_to) if decl.type_id and decl.date_to else False

    @api.depends('line_ids.value_amount', 'line_ids.is_total')
    def _compute_amount_total(self):
        for decl in self:
            decl.amount_total = sum(decl.line_ids.filtered('is_total').mapped('value_amount'))

    @api.depends('payment_ids.amount', 'amount_total')
    def _compute_amount_paid(self):
        for decl in self:
            decl.amount_paid = sum(decl.payment_ids.mapped('amount'))
            decl.amount_residual = decl.amount_total - decl.amount_paid

    @api.depends('issue_ids.severity')
    def _compute_issue_counts(self):
        for decl in self:
            severities = decl.issue_ids.mapped('severity')
            decl.blocking_count = severities.count(BLOCKING)
            decl.warning_count = len(severities) - decl.blocking_count

    # --- ORM -------------------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        # L'index unique partiel lit « state » en base : une annulation encore en cache doit être écrite.
        self.flush_model(['state', 'rectified_id'])
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get(ENGINE) and FROZEN_FIELDS & set(vals):
            frozen = self.filtered(lambda d: d.state in FROZEN_STATES)
            if frozen:
                raise UserError(
                    self.env._(
                        'La déclaration %(name)s est validée : elle ne peut plus être modifiée. '
                        'Créez une déclaration rectificative.',
                        name=frozen[0].name,
                    )
                )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_only_draft(self):
        if self.filtered(lambda d: d.state not in ('draft', 'cancel')):
            raise UserError(self.env._('Seule une déclaration brouillon ou annulée peut être supprimée.'))

    def copy(self, default=None):
        if not self.env.context.get(ENGINE):
            raise UserError(self.env._('Une déclaration ne se duplique pas : créez une rectificative.'))
        return super().copy(default)

    # --- State ----------------------------------------------------------------------------------

    def _ensure_state(self, target, sources=None):
        """Garde des transitions (patron 7) : ``target`` doit être accessible depuis l'état courant,
        et l'état courant faire partie de ``sources`` quand l'action l'exige."""
        labels = dict(STATES)
        for decl in self:
            if target not in self._TRANSITIONS[decl.state] or (sources and decl.state not in sources):
                raise UserError(
                    self.env._(
                        '%(name)s : passage de l’état « %(from)s » à « %(to)s » impossible.',
                        name=decl.name,
                        **{'from': labels[decl.state], 'to': labels[target]},
                    )
                )

    def _check_declarant(self):
        """Seul le déclarant fiscal valide, dépose et règle (prompt 04, 4.1)."""
        if not self.env.su and not self.env.user.has_group(DECLARANT_GROUP):
            raise UserError(self.env._('Action réservée au groupe « Déclarant fiscal ».'))

    def _engine(self):
        return self.with_context(**{ENGINE: True})

    # --- Template Method ----------------------------------------------------------------------

    def _generator(self):
        self.ensure_one()
        return self.env['l10n_ga.declaration.generator']._get(self.type_id.generator_key)

    def action_compute(self):
        for decl in self:
            # Un recalcul ne part jamais d'une déclaration validée (RG14) : « annuler la validation » d'abord.
            decl._ensure_state('computed', sources=('draft', 'computed'))
            decl._engine()._compute_declaration()
        return True

    def _compute_declaration(self):
        """Algorithme fixe ; les étapes variables sont déléguées au générateur (patron 6)."""
        self.ensure_one()
        generator = self._generator()
        facts = generator._collect(self)  # étape variable
        values = {**self._auto_values(), **generator._fill(self, facts)}  # étape variable
        self._write_boxes(values)
        self._write_details(generator._details(self, facts))  # étape variable
        self._run_checks(generator._checks(self, facts), facts)
        self.state = 'computed'
        if not self.blocking_count:
            self.activity_unlink([ACTIVITY_FIX])

    def _auto_values(self):
        company = self.company_id
        values = {
            'company_name': company.name,
            'company_nif': company.l10n_ga_nif,
            'company_cnss': company.l10n_ga_cnss_number,
            'company_cnamgs': company.l10n_ga_cnamgs_number,
            'company_street': company.street,
            'company_city': company.city,
            'company_phone': company.phone,
            'company_email': company.email,
            'company_website': company.website,
            'company_tax_center': company.l10n_ga_tax_center,
            'period_month': self.date_to.month,
            'period_quarter': (self.date_to.month - 1) // PERIOD_MONTHS['quarterly'] + 1,
            'period_year': self.date_to.year,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return {box.code: values[box.auto_value] for box in self.type_id.box_ids if box.auto_value}

    def _line_values(self, box, value):
        if value is None:  # case que le générateur ne renseigne pas (cadre vide, D-76)
            return {'value_blank': True}
        kind = box.value_kind
        if kind == 'amount':
            # Règle d'or 9 : arrondi au franc, case par case.
            return {'value_amount': float_round(value or 0.0, precision_digits=0)}
        if kind in ('number', 'rate'):
            return {'value_number': value or 0.0}
        if kind == 'date':
            return {'value_date': value or False}
        return {'value_text': '' if value in (None, False) else str(value)}

    def _write_boxes(self, values):
        boxes = {box.code: box for box in self.type_id.box_ids}
        unknown = set(values) - set(boxes)
        if unknown:
            raise UserError(
                self.env._(
                    'Cases inconnues de l’imprimé %(type)s : %(codes)s.',
                    type=self.type_id.code,
                    codes=', '.join(sorted(unknown)),
                )
            )
        self.line_ids.unlink()
        self.env['l10n_ga.declaration.line'].create(
            [
                {'declaration_id': self.id, 'box_id': box.id, **self._line_values(box, values.get(code))}
                for code, box in boxes.items()
            ]
        )

    def _write_details(self, details):
        boxes = {box.code: box for box in self.type_id.box_ids}
        self.detail_ids.unlink()
        vals_list = []
        for detail in details:
            box_code = detail.get('box_code')
            if box_code and box_code not in boxes:
                raise UserError(self.env._('Case inconnue dans le détail : %(code)s.', code=box_code))
            vals_list.append(
                {
                    'declaration_id': self.id,
                    'box_id': boxes[box_code].id if box_code else False,
                    'employee_id': detail.get('employee_id', False),
                    'partner_id': detail.get('partner_id', False),
                    'label': detail.get('label', False),
                    'amount': float_round(detail.get('amount') or 0.0, precision_digits=0),
                    'payload': detail.get('payload') or False,
                    'payslip_line_ids': [fields.Command.set(detail.get('payslip_line_ids') or [])],
                }
            )
        self.env['l10n_ga.declaration.detail'].create(vals_list)

    def _run_checks(self, generator_issues, facts):
        """Anomalies recréées à chaque calcul : contrôles communs puis ceux du générateur (RG15)."""
        Issue = self.env['l10n_ga.check.issue'].sudo()
        Issue.search([('declaration_id', '=', self.id)]).unlink()
        values = []
        for severity, code, message, record in [*run_checks(self, facts), *generator_issues]:
            values.append(
                {
                    'company_id': self.company_id.id,
                    'scope': 'declaration',
                    'declaration_id': self.id,
                    'employee_id': record.id if record._name == 'hr.employee' else False,
                    'severity': severity,
                    'code': code,
                    'message': message,
                    'res_model': record._name,
                    'res_id': record.id,
                }
            )
        Issue.create(values)

    # --- actions ---------------------------------------------------------------------------------

    def action_validate(self):
        self._check_declarant()
        for decl in self:
            decl._ensure_state('validated')
            blocking = decl.issue_ids.filtered(lambda i: i.severity == BLOCKING)
            if blocking:
                raise UserError(
                    self.env._('%(name)s ne peut pas être validée : anomalies bloquantes à corriger.', name=decl.name)
                    + '\n'
                    + '\n'.join(blocking.mapped('message'))
                )
            decl._engine()._snapshot()
        return True

    def action_unvalidate(self):
        """Annuler la validation (validée → calculée) : l'instantané et ses fichiers sont retirés."""
        self._check_declarant()
        for decl in self:
            decl._ensure_state('computed', sources=('validated',))
            if decl.payment_ids:
                raise UserError(self.env._('%(name)s : supprimez d’abord les quittances enregistrées.', name=decl.name))
            attachments = decl.snapshot_attachment_ids
            decl._engine().write(
                {'state': 'computed', 'sha256': False, 'validated_date': False, 'validated_by_id': False}
            )
            attachments.sudo().unlink()
            decl.message_post(body=self.env._('Validation annulée : instantané retiré.'))
        return True

    def action_mark_filed(self):
        self._check_declarant()
        for decl in self:
            decl._ensure_state('filed')
            decl.write({'state': 'filed', 'filing_date': decl.filing_date or fields.Date.context_today(decl)})
            decl.activity_feedback([ACTIVITY_DUE])
            decl._l10n_ga_update_payment_state()  # quittances déjà enregistrées à la validation
        return True

    def action_mark_paid(self):
        """RG16 : « payée » seulement quand les quittances couvrent le total dû."""
        self._check_declarant()
        for decl in self:
            decl._ensure_state('paid')
            if not decl._is_covered():
                raise UserError(
                    self.env._(
                        '%(name)s : quittances %(paid)s pour %(total)s dus.',
                        name=decl.name,
                        paid=decl.amount_paid,
                        total=decl.amount_total,
                    )
                )
            decl.state = 'paid'
        return True

    def _is_covered(self):
        self.ensure_one()
        return float_compare(self.amount_paid, self.amount_total, precision_rounding=self.currency_id.rounding) >= 0

    def _l10n_ga_update_payment_state(self):
        """Après chaque quittance (F11, RG16, D-78) : « déposée » ↔ « payée », sur-paiement signalé."""
        Issue = self.env['l10n_ga.check.issue'].sudo()
        for decl in self:
            engine = decl._engine()
            if decl.state == 'filed' and decl._is_covered():
                engine.state = 'paid'
                decl.message_post(body=self.env._('Quittances couvrant le total dû : déclaration payée.'))
            elif decl.state == 'paid' and not decl._is_covered():
                engine.state = 'filed'
                decl.message_post(body=self.env._('Quittances insuffisantes : déclaration repassée « déposée ».'))
            Issue.search([('declaration_id', '=', decl.id), ('code', '=', OVERPAID)]).unlink()
            rounding = decl.currency_id.rounding
            if float_compare(decl.amount_paid, decl.amount_total, precision_rounding=rounding) > 0:
                message = self.env._(
                    'Sur-paiement : %(paid)s versés pour %(total)s dus.', paid=decl.amount_paid, total=decl.amount_total
                )
                Issue.create(
                    {
                        'company_id': decl.company_id.id,
                        'scope': 'declaration',
                        'declaration_id': decl.id,
                        'severity': 'warning',
                        'code': OVERPAID,
                        'message': message,
                        'res_model': decl._name,
                        'res_id': decl.id,
                    }
                )
                decl.message_post(body=message)

    def action_reset_draft(self):
        for decl in self:
            decl._ensure_state('draft')
            engine = decl._engine()
            engine.line_ids.unlink()
            engine.detail_ids.unlink()
            decl.issue_ids.sudo().unlink()
            decl.state = 'draft'
        return True

    def action_cancel(self):
        for decl in self:
            decl._ensure_state('cancel')
            decl.state = 'cancel'
            decl.activity_unlink([ACTIVITY_DUE, ACTIVITY_FIX])
        return True

    def action_create_rectification(self):
        """Déclaration rectificative (RG14) : l'originale déposée reste intacte."""
        self.ensure_one()
        if self.state not in ('filed', 'paid'):
            raise UserError(self.env._('Seule une déclaration déposée ou payée se rectifie.'))
        rectification = self.create(
            {
                'company_id': self.company_id.id,
                'type_id': self.type_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'due_date': self.due_date,
                'rectified_id': self.id,
            }
        )
        self.message_post(body=self.env._('Rectificative créée : %(name)s.', name=rectification.name))
        return rectification._get_records_action(name=self.env._('Rectificative'))

    def action_check_integrity(self):
        self.ensure_one()
        ok = self._integrity_ok()
        message = (
            self.env._('Empreinte conforme : la déclaration n’a pas changé depuis sa validation.')
            if ok
            else self.env._('Empreinte NON conforme : les valeurs figées ont été altérées.')
        )
        self.message_post(body=message)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'message': message, 'type': 'success' if ok else 'danger', 'sticky': not ok},
        }

    # --- Snapshot -------------------------------------------------------------------------------

    def _snapshot_payload(self):
        """Contenu canonique de l'instantané (cases et détails), base de l'empreinte."""
        self.ensure_one()
        lines = sorted(
            [
                line.box_id.code,
                line.value_amount,
                line.value_number,
                line.value_text or '',
                str(line.value_date or ''),
                line.value_blank,
            ]
            for line in self.line_ids
        )
        details = sorted(
            (
                [
                    detail.box_id.code or '',
                    detail.employee_id.id or 0,
                    detail.partner_id.id or 0,
                    detail.label or '',
                    detail.amount,
                    json.dumps(detail.payload or {}, sort_keys=True, default=str),
                ]
                for detail in self.detail_ids
            ),
            key=lambda row: [str(value) for value in row],
        )
        return {
            'type': self.type_id.code,
            'company': self.company_id.id,
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'rectified': self.rectified_id.id or 0,
            'lines': lines,
            'details': details,
        }

    def _compute_sha256_value(self):
        payload = json.dumps(self._snapshot_payload(), sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _integrity_ok(self):
        self.ensure_one()
        return bool(self.sha256) and self.sha256 == self._compute_sha256_value()

    def _snapshot(self):
        """Figement (patron 10) : empreinte, fichiers Excel et PDF joints, auteur et date."""
        self.ensure_one()
        self.write(
            {
                'sha256': self._compute_sha256_value(),
                'validated_date': fields.Datetime.now(),
                'validated_by_id': self.env.user.id,
            }
        )
        attachments = self._render_attachments()  # l'empreinte figure sur le PDF
        self.write({'state': 'validated', 'snapshot_attachment_ids': [fields.Command.set(attachments.ids)]})

    def _attachment(self, name, content, mimetype):
        return (
            self.env['ir.attachment']
            .sudo()
            .create(
                {
                    'name': name,
                    'datas': base64.b64encode(content),
                    'mimetype': mimetype,
                    'res_model': self._name,
                    'res_id': self.id,
                }
            )
        )

    def _file_basename(self):
        return f'{self.type_id.code}_{self.company_id.name}_{self.date_from:%Y%m}-{self.date_to:%Y%m}'.replace(
            ' ', '_'
        ).replace('/', '-')

    def _render_attachments(self):
        content, extension = self._render_xlsx()
        mimetype = (
            'application/vnd.ms-excel.sheet.macroEnabled.12'
            if extension == 'xlsm'
            else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        attachments = self._attachment(f'{self._file_basename()}.{extension}', content, mimetype)
        pdf, report_type = self._render_pdf()
        if report_type == 'pdf':
            attachments |= self._attachment(f'{self._file_basename()}.pdf', pdf, 'application/pdf')
        else:  # mode test : Odoo rend le HTML du rapport (ir_actions_report.py:1030)
            attachments |= self._attachment(f'{self._file_basename()}.html', pdf, 'text/html')
        return attachments

    def _box_cells(self):
        return [
            (line.box_id.cell_ref, line._value(), AMOUNT_FORMAT if line.box_id.value_kind == 'amount' else None)
            for line in self.line_ids
            if line.box_id.cell_ref
        ]

    def _render_xlsx(self):
        """Builder (patron 9) : gabarit officiel rempli, sinon classeur neuf. Valeurs uniquement."""
        self.ensure_one()
        template = self.type_id._template_bytes()
        if template:
            builder = XlsmTemplateRenderer(template)
            builder.boxes(self._box_cells())
            extension = 'xlsm' if self.type_id.template_path.lower().endswith('.xlsm') else 'xlsx'
            return builder.build(), extension
        return self._render_new_workbook(), 'xlsx'

    def _render_new_workbook(self):
        """Classeur neuf mis en forme (sans gabarit officiel : DTS, DAS…)."""
        own = self._generator()._render_workbook(self)
        if own is not None:
            return own
        env = self.env
        builder = XlsxDeclarationBuilder(title=self.type_id.name, subtitle=self.name)
        auto_lines = self.line_ids.filtered(lambda line: line.box_id.auto_value)
        # Année, mois, trimestre : des repères, pas des montants (écrits en texte).
        identity = {
            line.box_id.name: f'{line._value():.0f}' if line.box_id.value_kind == 'number' else line._value()
            for line in auto_lines
        }
        identity.setdefault(env._('Raison sociale'), self.company_id.name)
        identity.setdefault(env._('NIF'), self.company_id.l10n_ga_nif or '')
        identity[env._('Période')] = env._(
            'du %(start)s au %(end)s', start=f'{self.date_from:%d/%m/%Y}', end=f'{self.date_to:%d/%m/%Y}'
        )
        identity[env._('Échéance')] = self.due_date
        identity[env._('État')] = dict(STATES)[self.state]
        builder.header(identity)
        lines = self.line_ids - auto_lines
        builder.boxes(
            [env._('Case'), env._('Désignation'), env._('Montant')],
            [(line.box_id.code, line.box_id.name, line._value()) for line in lines],
            bold=lines.filtered(lambda line: line.box_id.sum_box_codes).mapped('code'),
        )
        columns = self._l10n_ga_detail_columns()
        if columns:  # état nominatif (DTS, DAS) : une ligne par salarié, colonnes du générateur
            rows = [[self._l10n_ga_cell(detail, column) for column in columns] for detail in self.detail_ids]
            totals = [
                sum(row[index] or 0 for row in rows) if column[2] == 'amount' else None
                for index, column in enumerate(columns)
            ]
            totals[0] = env._('Total')
            builder.table(
                env._('État nominatif'),
                0,
                rows,
                headers=[column[1] for column in columns],
                title=env._('%(type)s — état nominatif — %(name)s', type=self.type_id.name, name=self.name),
                totals=totals,
            )
        else:
            builder.table(
                env._('Détails'),
                0,
                [(detail.box_id.code, detail.label, detail.amount) for detail in self.detail_ids],
                headers=[env._('Case'), env._('Salarié / tiers'), env._('Montant')],
                title=env._('%(type)s — détail — %(name)s', type=self.type_id.name, name=self.name),
            )
        return builder.build()

    @staticmethod
    def _l10n_ga_cell(detail, column):
        """Valeur d'une colonne de l'état nominatif (dates ISO du détail → dates)."""
        value = (detail.payload or {}).get(column[0])
        if column[2] == 'date' and value:
            return fields.Date.to_date(value)
        return value

    def _l10n_ga_detail_columns(self):
        """Colonnes du détail nominatif, fournies par le générateur (rendus Excel et PDF)."""
        self.ensure_one()
        return self._generator()._detail_columns(self)

    def _l10n_ga_excel_html(self, page_width_px):
        """Le PDF reproduit le classeur de la déclaration : celui de l'instantané s'il existe, sinon le
        classeur calculé sur les valeurs stockées (identique, puisque rendu depuis les mêmes champs)."""
        self.ensure_one()
        excel = self.snapshot_attachment_ids.filtered(lambda a: a.name.endswith(('.xlsx', '.xlsm')))[:1]
        content = base64.b64decode(excel.datas) if excel else self._render_xlsx()[0]
        return Markup(workbook_to_html(content, page_width_px))

    def _render_pdf(self):
        self.ensure_one()
        report = self.type_id.report_id or self.env.ref('l10n_ga_dgi_edi.action_report_declaration')
        return self.env['ir.actions.report'].sudo()._render_qweb_pdf(report, self.ids)

    # --- Observer : bulletins et échéances (ADR-10) --------------------------------------------

    def _l10n_ga_auto_types(self):
        registry = self.env['l10n_ga.declaration.generator']
        types = self.env['l10n_ga.declaration.type'].sudo().search([('auto_create', '=', True)])
        return types.filtered(lambda t: registry._has(t.generator_key))

    @api.model
    def _l10n_ga_prepare(self, company, decl_type, date_from, date_to):
        """Déclaration active de la période : créée si absente, recalculée tant qu'elle n'est pas figée."""
        Declaration = self.sudo()
        declaration = Declaration.search(
            [
                ('company_id', '=', company.id),
                ('type_id', '=', decl_type.id),
                ('date_from', '=', date_from),
                ('date_to', '=', date_to),
                ('rectified_id', '=', False),
                ('state', '!=', 'cancel'),
            ],
            limit=1,
        )
        if not declaration:
            declaration = Declaration.create(
                {'company_id': company.id, 'type_id': decl_type.id, 'date_from': date_from, 'date_to': date_to}
            )
        if declaration.state in ('draft', 'computed'):
            declaration.action_compute()
        return declaration

    @api.model
    def _l10n_ga_on_payslips_done(self, slips):
        """Bulletins validés, payés, annulés ou remis en brouillon : déclarations de leur période à jour."""
        slips = slips.filtered('l10n_ga_is_ga')
        periods = set()
        for decl_type in self._l10n_ga_auto_types().filtered('prepare_on_payslip'):
            generator = self.env['l10n_ga.declaration.generator']._get(decl_type.generator_key)
            for slip in slips.filtered(lambda s, generator=generator: generator._applies(s.company_id)):
                day = slip.l10n_ga_payment_date if decl_type.period_basis == 'payment_date' else slip.date_to
                if day and decl_type._is_active_on(day):
                    periods.add((slip.company_id, decl_type, *decl_type._period_bounds(day)))
        for company, decl_type, date_from, date_to in sorted(
            periods, key=lambda p: (p[0].id, p[1].sequence, p[1].id, p[2])
        ):
            declaration = self._l10n_ga_prepare(company, decl_type, date_from, date_to)
            if declaration.state in FROZEN_STATES:
                declaration.message_post(
                    body=self.env._(
                        'Des bulletins de la période ont changé après la validation : '
                        'les valeurs figées sont conservées ; une rectificative est peut-être nécessaire.'
                    )
                )

    def _l10n_ga_declarant(self):
        self.ensure_one()
        if self.company_id.l10n_ga_declarant_id:
            return self.company_id.l10n_ga_declarant_id
        group = self.env.ref(DECLARANT_GROUP)
        return (
            group.sudo()
            .all_user_ids.filtered(lambda u: not u.share and self.company_id in u.company_ids)
            .sorted('id')[:1]
        )

    def _l10n_ga_schedule_activities(self):
        """Activité « à déposer » pour le déclarant, « à corriger » s'il reste une anomalie bloquante."""
        for decl in self.filtered(lambda d: d.state in ('draft', 'computed', 'validated')):
            user = decl._l10n_ga_declarant()
            if not user:
                decl.message_post(body=self.env._('Aucun déclarant fiscal : définissez-le sur la société.'))
                continue
            if not decl.activity_search([ACTIVITY_DUE]):
                decl.activity_schedule(
                    ACTIVITY_DUE,
                    date_deadline=decl.due_date,
                    user_id=user.id,
                    summary=self.env._('%(name)s à déposer avant le %(date)s', name=decl.name, date=decl.due_date),
                )
            if decl.blocking_count and not decl.activity_search([ACTIVITY_FIX]):
                decl.activity_schedule(
                    ACTIVITY_FIX,
                    date_deadline=fields.Date.context_today(decl),
                    user_id=user.id,
                    summary=self.env._(
                        '%(name)s : %(count)s anomalie(s) bloquante(s)', name=decl.name, count=decl.blocking_count
                    ),
                )

    @api.model
    def _cron_prepare_due_declarations(self, today=None):
        """Cron quotidien : déclarations dont l'échéance tombe dans les ``lead_days`` jours (J-10)."""
        today = today or fields.Date.context_today(self)
        companies = self.env['res.company'].sudo().search([('partner_id.country_id.code', '=', 'GA')])
        for decl_type in self._l10n_ga_auto_types():
            horizon = today + timedelta(days=decl_type.lead_days)
            anchors = {day - relativedelta(months=decl_type.due_months) for day in (today, horizon)}
            periods = {decl_type._period_bounds(anchor) for anchor in anchors}
            for date_from, date_to in sorted(periods):
                due = decl_type._due_date(date_to)
                if not (today <= due <= horizon and decl_type._is_active_on(date_to)):
                    continue
                generator = self.env['l10n_ga.declaration.generator']._get(decl_type.generator_key)
                for company in companies.filtered(generator._applies):
                    declaration = self._l10n_ga_prepare(company, decl_type, date_from, date_to)
                    declaration._l10n_ga_schedule_activities()
