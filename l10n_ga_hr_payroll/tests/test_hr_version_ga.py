from datetime import date

from odoo.tests import tagged

from .common import GaPayrollCase


@tagged('post_install', '-at_install')
class TestHrVersionGa(GaPayrollCase):
    """Données Gabon de la version (ADR-05) et options de la société."""

    def _nationality(self, country_xmlid):
        country = self.env.ref(country_xmlid) if country_xmlid else self.env['res.country']
        employee = self._employee(f'Nationalité {country_xmlid}', 200_000, country_id=country.id)
        return employee.version_id.l10n_ga_nationality_code

    def test_nationality_code_from_country(self):
        self.assertEqual(self._nationality('base.ga'), '1')
        self.assertEqual(self._nationality('base.cm'), '2')
        self.assertEqual(self._nationality('base.sn'), '3')
        self.assertEqual(self._nationality('base.fr'), '4')
        self.assertFalse(self._nationality(None))

    def test_country_groups_are_data(self):
        cemac = self.env.ref('l10n_ga_hr_payroll.country_group_cemac')
        africa = self.env.ref('l10n_ga_hr_payroll.country_group_africa')
        self.assertEqual(len(cemac.country_ids), 6)
        self.assertLessEqual(cemac.country_ids, africa.country_ids)
        self.assertEqual(len(africa.country_ids), 54)

    def test_defaults(self):
        employee = self._employee('Défauts', 200_000)
        self.assertEqual(employee.l10n_ga_payment_mode, 'transfer')
        self.assertFalse(employee.l10n_ga_transport_trips)
        self.assertEqual(employee.version_id._l10n_ga_benefit_kinds(), ())

    def test_benefit_kinds_in_core_order(self):
        employee = self._employee('Avantages', 200_000, l10n_ga_benefit_food=True, l10n_ga_benefit_housing=True)
        self.assertEqual(employee.version_id._l10n_ga_benefit_kinds(), ('housing', 'food'))

    def test_company_cash_rounding_default_from_parameter(self):
        expected = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_ga_cash_rounding_default', date.today())
        self.assertEqual(self.company.l10n_ga_cash_rounding, expected)
        self.assertEqual(self.company.l10n_ga_cfp_base, 'social')
        self.assertEqual(self.company.l10n_ga_cfp_declaration, 'id10')

    def test_company_fiscal_params_with_options(self):
        self.company.l10n_ga_cfp_base = 'gross'
        params = self.company._l10n_ga_fiscal_params(date(2026, 9, 30))
        self.assertEqual(params.cfp_base, 'gross')
        self.assertEqual(params.cash_rounding, self.company.l10n_ga_cash_rounding)
        self.assertEqual(params.fnh_rate, 0.03)

    def test_post_init_hook_recomputes_existing_versions(self):
        from .. import _post_init_hook  # noqa: PLC0415

        version = self._employee('Reprise', 200_000, country_id=self.env.ref('base.cm').id).version_id
        self.env.cr.execute(
            'UPDATE hr_version SET l10n_ga_tax_parts = 0, l10n_ga_nationality_code = NULL WHERE id = %s', [version.id]
        )
        version.invalidate_recordset()
        _post_init_hook(self.env)
        self.assertEqual((version.l10n_ga_tax_parts, version.l10n_ga_nationality_code), (1.0, '2'))
