"""Vue ID10 et imprimés au format de la V1 (ADR-20, FIX 03).

Tout ce qui est affiché ou imprimé est **lu** sur les cases et détails stockés de la déclaration
(``line_ids``, ``detail_ids``) : aucun recalcul. Les champs ``id10_*`` sont des champs d'affichage non
stockés de la vue ID10 ; la valeur déclarée reste celle, figée, de la case (règle d'or 8).
"""

from babel.dates import format_date as babel_format_date

from odoo import api, fields, models

try:
    from num2words import num2words
except ImportError:  # pragma: no cover — dépendance d'Odoo (montants en lettres)
    num2words = None

# Champ d'affichage de la vue ID10 → code de la case (données l10n_ga_declaration_type_data.xml)
ID10_AMOUNT_BOXES = {
    'id10_irpp': 'L40',
    'id10_tcs': 'L41',
    'id10_fnh': 'L42',
    'id10_withholding_total': 'L43',
    'id10_cfp_l1': 'R49',
    'id10_cfp_l2': 'R50',
    'id10_cfp_l3': 'R51',
    'id10_cfp_l4': 'R52',
    'id10_cfp_l5': 'R53',
    'id10_cfp_base': 'R54',
    'id10_cfp_amount': 'R56',
}
ID10_TEXT_BOXES = {
    'id10_nif': 'HDR_NIF',
    'id10_company_name': 'HDR_NAME',
    'id10_street': 'HDR_STREET',
    'id10_city': 'HDR_CITY',
    'id10_phone': 'HDR_PHONE',
    'id10_email': 'HDR_EMAIL',
    'id10_website': 'HDR_WEB',
    'id10_tax_center': 'HDR_TAX_CENTER',
}
ID10_RATE_BOX = 'R55'
PERCENT = 100
FORM_LOCALE = 'fr_FR'  # les imprimés DGI sont en français, quelle que soit la langue de l'utilisateur
FORM_LANG = 'fr'
CURRENCY_UNITS = {'XAF': 'francs CFA'}
# Imprimé du formulaire par type : gabarit QWeb appelé par le rapport commun de chaque format de page.
FORM_TEMPLATES = {
    'ID10': 'l10n_ga_dgi_edi.form_id10',
    'ID28': 'l10n_ga_dgi_edi.form_id28',
    'DTS_CNSS': 'l10n_ga_dgi_edi.form_dts',
    'DTS_CNAMGS': 'l10n_ga_dgi_edi.form_dts',
    'DAS': 'l10n_ga_dgi_edi.form_das',
}
GENERIC_FORM_TEMPLATE = 'l10n_ga_dgi_edi.form_generic'
# Rendu PDF du classeur Excel par type (format de page adapté), rapport générique sinon.
WORKBOOK_REPORTS = {
    'ID10': 'l10n_ga_dgi_edi.action_report_id10',
    'ID28': 'l10n_ga_dgi_edi.action_report_id28',
    'DTS_CNSS': 'l10n_ga_dgi_edi.action_report_dts',
    'DTS_CNAMGS': 'l10n_ga_dgi_edi.action_report_dts',
    'DAS': 'l10n_ga_dgi_edi.action_report_das',
}
GENERIC_WORKBOOK_REPORT = 'l10n_ga_dgi_edi.action_report_declaration'


class L10nGaDeclaration(models.Model):
    _inherit = 'l10n_ga.declaration'

    amount_total_words = fields.Char(string='Total en lettres', compute='_compute_amount_total_words')
    id10_irpp = fields.Monetary(string='IRPP', compute='_compute_id10_values')
    id10_tcs = fields.Monetary(string='TCS', compute='_compute_id10_values')
    id10_fnh = fields.Monetary(string='FNH', compute='_compute_id10_values')
    id10_withholding_total = fields.Monetary(string='Montant global dû (retenues)', compute='_compute_id10_values')
    id10_cfp_l1 = fields.Monetary(string='L1 — Salaire de base', compute='_compute_id10_values')
    id10_cfp_l2 = fields.Monetary(string='L2 — Avantages en numéraire', compute='_compute_id10_values')
    id10_cfp_l3 = fields.Monetary(string='L3 — Cotisations CNSS', compute='_compute_id10_values')
    id10_cfp_l4 = fields.Monetary(string='L4 — Cotisations CNAMGS', compute='_compute_id10_values')
    id10_cfp_l5 = fields.Monetary(string='L5 — Avantages en nature', compute='_compute_id10_values')
    id10_cfp_base = fields.Monetary(string='L6 — Base CFP', compute='_compute_id10_values')
    id10_cfp_rate = fields.Float(string='L7 — Taux (%)', digits=(5, 2), compute='_compute_id10_values')
    id10_cfp_amount = fields.Monetary(string='Montant CFP (L6 × L7)', compute='_compute_id10_values')
    id10_cfp_blank = fields.Boolean(string='CFP déclarée sur l’ID28', compute='_compute_id10_values')
    id10_nif = fields.Char(string='NIF', compute='_compute_id10_values')
    id10_company_name = fields.Char(string='Raison sociale', compute='_compute_id10_values')
    id10_street = fields.Char(string='Boîte postale', compute='_compute_id10_values')
    id10_city = fields.Char(string='Ville', compute='_compute_id10_values')
    id10_phone = fields.Char(string='Téléphone', compute='_compute_id10_values')
    id10_email = fields.Char(string='Adresse e-mail', compute='_compute_id10_values')
    id10_website = fields.Char(string='Site Internet', compute='_compute_id10_values')
    id10_tax_center = fields.Char(string='Code de résidence', compute='_compute_id10_values')

    @api.depends('line_ids.value_amount', 'line_ids.value_number', 'line_ids.value_text', 'line_ids.value_blank')
    def _compute_id10_values(self):
        for decl in self:
            values = decl._l10n_ga_values()
            for field_name, code in ID10_AMOUNT_BOXES.items():
                decl[field_name] = values.get(code) or 0.0
            for field_name, code in ID10_TEXT_BOXES.items():
                decl[field_name] = values.get(code) or False
            decl.id10_cfp_rate = (values.get(ID10_RATE_BOX) or 0.0) * PERCENT
            decl.id10_cfp_blank = ID10_RATE_BOX in values and values[ID10_RATE_BOX] is None

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_words(self):
        for decl in self:
            decl.amount_total_words = decl._l10n_ga_words(decl.amount_total) if decl.amount_total else False

    # --- lecture des valeurs figées ------------------------------------------------------------

    def _l10n_ga_words(self, amount):
        """Montant en lettres, en français (« Arrêté le présent imprimé à la somme de … »)."""
        self.ensure_one()
        if num2words is None:  # pragma: no cover
            return self.currency_id.amount_to_text(amount)
        unit = CURRENCY_UNITS.get(self.currency_id.name, self.currency_id.currency_unit_label or '')
        return f'{num2words(round(amount), lang=FORM_LANG)} {unit}'.strip()

    def _l10n_ga_values(self):
        """``{code de case: valeur}`` lue sur les cases stockées ; ``None`` = case laissée vide."""
        self.ensure_one()
        return {line.box_id.code: line._value() for line in self.line_ids}

    def _l10n_ga_names(self):
        """``{code de case: libellé}`` des cases de l'imprimé."""
        self.ensure_one()
        return {box.code: box.name for box in self.type_id.box_ids}

    def _l10n_ga_details(self, box_code=None, employees=None):
        """Charges utiles des détails (état nominatif, bénéficiaires, quittances), dans l'ordre stocké.

        ``box_code`` : détails d'une case ; ``employees`` : vrai = lignes par salarié seulement.
        """
        self.ensure_one()
        details = self.detail_ids
        if box_code is not None:
            details = details.filtered(lambda d: d.box_id.code == box_code)
        if employees:
            details = details.filtered('employee_id')
        return [{**(detail.payload or {}), '_amount': detail.amount, '_label': detail.label} for detail in details]

    def _l10n_ga_fmt(self, value, digits=0):
        """Montant au format de l'imprimé (« 1 234 567 », comme le classeur), vide si la case est vide."""
        if value is None or value is False or value == '':
            return ''
        if isinstance(value, str):
            return value
        text = f'{value:,.{digits}f}'.replace(',', '\u202f')  # comme le rendu du classeur
        return text.replace('.', ',') if digits else text

    def _l10n_ga_date(self, value):
        """Date au format de la langue (les détails stockent les dates en texte ISO)."""
        if not value:
            return ''
        return babel_format_date(fields.Date.to_date(value), 'dd/MM/yyyy', locale=FORM_LOCALE)

    def _l10n_ga_month_label(self):
        """« Septembre 2026 » : mois de la période."""
        self.ensure_one()
        return babel_format_date(self.date_to, 'MMMM yyyy', locale=FORM_LOCALE).capitalize()

    def _l10n_ga_payment_modes(self):
        """Modes de versement des quittances, libellés distincts (cadre « Règlement »)."""
        self.ensure_one()
        labels = dict(self.env['l10n_ga.declaration.payment']._fields['mode']._description_selection(self.env))
        return ', '.join(dict.fromkeys(labels[mode] for mode in self.payment_ids.mapped('mode')))

    def _l10n_ga_parameter(self, code):
        """Paramètre daté en vigueur à la fin de la période (seuils affichés sur l'imprimé)."""
        self.ensure_one()
        return (
            self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(code, self.date_to, raise_if_not_found=False)
        )

    def _l10n_ga_form_template(self):
        self.ensure_one()
        return FORM_TEMPLATES.get(self.type_id.code, GENERIC_FORM_TEMPLATE)

    # --- actions -----------------------------------------------------------------------------------

    def action_print_form(self):
        """Imprimé officiel de la déclaration (rapport du type, format V1 — ADR-20)."""
        self.ensure_one()
        report = self.type_id.report_id or self.env.ref('l10n_ga_dgi_edi.action_report_form_portrait')
        return report.report_action(self, config=False)  # imprimé autonome : pas de mise en page société

    def _l10n_ga_workbook_report(self):
        self.ensure_one()
        return self.env.ref(WORKBOOK_REPORTS.get(self.type_id.code, GENERIC_WORKBOOK_REPORT))

    def action_print_workbook(self):
        """Rendu PDF du classeur Excel (contrôle visuel du .xlsx / .xlsm)."""
        self.ensure_one()
        return self._l10n_ga_workbook_report().report_action(self, config=False)
