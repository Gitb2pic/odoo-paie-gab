"""Imprimés au format de la V1 des déclarations de la comptabilité (ADR-20, FIX 03)."""

from odoo import models

FORM_TEMPLATES = {
    'ID18': 'l10n_ga_dgi_edi_account.form_withholding',
    'ID27': 'l10n_ga_dgi_edi_account.form_withholding',
    'ID23': 'l10n_ga_dgi_edi_account.form_fees',
    'ID24': 'l10n_ga_dgi_edi_account.form_fees',
    'ID26': 'l10n_ga_dgi_edi_account.form_fees',
}
WORKBOOK_REPORTS = {
    'ID23': 'l10n_ga_dgi_edi_account.action_report_das_annex',
    'ID24': 'l10n_ga_dgi_edi_account.action_report_das_annex',
    'ID26': 'l10n_ga_dgi_edi_account.action_report_das_annex',
}


class L10nGaDeclaration(models.Model):
    _inherit = 'l10n_ga.declaration'

    def _l10n_ga_form_template(self):
        return FORM_TEMPLATES.get(self.type_id.code) or super()._l10n_ga_form_template()

    def _l10n_ga_workbook_report(self):
        code = WORKBOOK_REPORTS.get(self.type_id.code)
        return self.env.ref(code) if code else super()._l10n_ga_workbook_report()

    def _l10n_ga_fee_sections(self):
        """Annexes ID23, ID24, ID26 : ``[(libellé, lignes)]`` par section du générateur, lues sur les détails."""
        self.ensure_one()
        rows = self._l10n_ga_details()
        return [
            (label, [row for row in rows if row.get('section') == section])
            for section, _box, label in self._generator()._sections
        ]

    def _l10n_ga_fee_columns(self):
        """Colonnes ``[(clé, libellé)]`` de l'annexe (celles du classeur)."""
        self.ensure_one()
        return self._generator()._columns()
