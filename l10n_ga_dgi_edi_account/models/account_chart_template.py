from odoo import models
from odoo.addons.account.models.chart_template import template

MODULE = 'l10n_ga_dgi_edi_account'
SEQUENCE_PREFIX = {'ras_095': 'RAS095', 'ras_20': 'RAS20'}
TEMPLATE = 'ga'  # plan SYSCOHADA des entreprises ; le plan des associations n'a pas le compte 4478 (cf. D-62)


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template(TEMPLATE, 'account.tax.group')
    def _get_ga_dgi_edi_account_tax_group(self):
        return self._parse_csv(TEMPLATE, 'account.tax.group', module=MODULE)

    @template(TEMPLATE, 'account.tax')
    def _get_ga_dgi_edi_account_tax(self):
        return self._parse_csv(TEMPLATE, 'account.tax', module=MODULE)

    @template(TEMPLATE, 'account.fiscal.position')
    def _get_ga_dgi_edi_account_fiscal_position(self):
        return self._parse_csv(TEMPLATE, 'account.fiscal.position', module=MODULE)

    def _post_load_data(self, template_code, company, template_data):
        result = super()._post_load_data(template_code, company, template_data)
        if template_code == TEMPLATE:
            self._l10n_ga_withholding_setup(company)
        return result

    def _l10n_ga_load_withholding(self, companies):
        """Sociétés déjà équipées du plan : charge les retenues absentes (installation, idempotent)."""
        for company in companies:
            chart = self.with_company(company)
            data = {
                'account.tax.group': chart._get_ga_dgi_edi_account_tax_group(),
                'account.tax': chart._get_ga_dgi_edi_account_tax(),
                'account.fiscal.position': chart._get_ga_dgi_edi_account_fiscal_position(),
            }
            missing = {
                model: {
                    xmlid: values for xmlid, values in records.items() if not chart.ref(xmlid, raise_if_not_found=False)
                }
                for model, records in data.items()
            }
            if any(missing.values()):
                chart._load_data(missing)
            self._l10n_ga_withholding_setup(company)

    def _l10n_ga_withholding_setup(self, company):
        self._l10n_ga_withholding_sequences(company)
        # Tiers déjà classés : position fiscale « RAS » dans la société nouvellement équipée (D-96).
        partners = (
            self.env['res.partner'].with_context(active_test=False).search([('l10n_ga_withholding_kind', '!=', False)])
        )
        partners._l10n_ga_apply_withholding_position()

    def _l10n_ga_withholding_sequences(self, company):
        """Une séquence de pièces de retenue par taxe : numéros proposés au paiement (sprint 0 point 7)."""
        for tax in (
            self.env['account.tax']
            ._l10n_ga_withholding_taxes(company)
            .filtered(lambda t: not t.withholding_sequence_id)
        ):
            tax.withholding_sequence_id = (
                self.env['ir.sequence']
                .sudo()
                .create(
                    {
                        'name': tax.name,
                        'code': f'l10n_ga.{tax.l10n_ga_withholding_kind}',
                        'prefix': SEQUENCE_PREFIX[tax.l10n_ga_withholding_kind] + '/%(year)s/',
                        'padding': 5,
                        'implementation': 'no_gap',
                        'company_id': company.id,
                    }
                )
            )
