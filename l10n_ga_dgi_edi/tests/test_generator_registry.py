from datetime import date
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from ..models.declaration_generator import L10nGaDeclarationGenerator
from .common import F16_CNSS, F16_FNH, F16_IRPP, F16_TCS, FakeGenerator, GaDeclarationCase

DEC_2025 = (date(2025, 12, 1), date(2025, 12, 31))
JAN_2026 = (date(2026, 1, 1), date(2026, 1, 31))


@tagged('post_install', '-at_install')
class TestGeneratorRegistry(GaDeclarationCase):
    """Patrons 4-6 : registre, stratégie factice, générateur générique « payslip » (Template Method)."""

    def test_registry(self):
        registry = self.env['l10n_ga.declaration.generator']
        self.assertEqual(registry._get('payslip')._name, 'l10n_ga.declaration.generator.payslip')
        self.assertEqual(registry._get(' PAYSLIP ')._name, 'l10n_ga.declaration.generator.payslip')
        self.assertFalse(registry._has('base'))
        self.assertFalse(registry._has(False))
        with self.assertRaises(KeyError):
            registry._get('inconnu')
        with self.assertRaises(ValidationError):
            self.env['l10n_ga.declaration.type'].create({'code': 'X', 'name': 'X', 'generator_key': 'inconnu'})
        base = self.env['l10n_ga.declaration.generator.base']
        with self.assertRaises(NotImplementedError):
            base._collect(self._declaration())
        with self.assertRaises(NotImplementedError):
            base._fill(self._declaration(decl_type=self._declaration_type('T_BASE')), {})
        self.assertEqual(
            (base._details(None, {}), base._checks(None, {}), base._required_parameters(None)), ([], [], [])
        )

    def test_fake_generator_template_method(self):
        fake = FakeGenerator(values={'B_IRPP': 1_000.6, 'B_TCS': 99.4, 'B_FNH': 0})
        with (
            patch.object(L10nGaDeclarationGenerator, '_has', lambda registry, key: True),
            patch.object(L10nGaDeclarationGenerator, '_get', lambda registry, key: fake),
        ):
            decl_type = self._declaration_type('T_FAKE', generator_key='fake')
            decl_type.box_ids = [Command.create({'code': 'R_RATE', 'name': 'Taux', 'value_kind': 'rate'})]
            fake.values['R_RATE'] = 0.005
            declaration = self._declaration(decl_type=decl_type)
            declaration.action_compute()
        self.assertEqual([call[0] for call in fake.calls], ['collect', 'fill'])
        self.assertEqual(fake.calls[1][1], {'facts': True})  # faits passés de _collect à _fill
        self.assertEqual(self._box(declaration, 'B_IRPP').value_amount, 1_001)  # arrondi au franc par case
        self.assertEqual(self._box(declaration, 'B_TCS').value_amount, 99)
        self.assertEqual(self._box(declaration, 'R_RATE').value_number, 0.005)  # taux non arrondi
        self.assertEqual(self._box(declaration, 'HDR_NIF').value_text, 'NIF-TEST')
        self.assertEqual(self._box(declaration, 'HDR_MONTH').value_number, 9)
        self.assertEqual(declaration.amount_total, 1_100)
        self.assertEqual(len(declaration.line_ids), len(decl_type.box_ids))

    def test_unknown_box_rejected(self):
        fake = FakeGenerator(values={'NOPE': 1})
        with patch.object(L10nGaDeclarationGenerator, '_get', lambda registry, key: fake):
            declaration = self._declaration()
            with self.assertRaisesRegex(UserError, 'NOPE'):
                declaration.action_compute()
        fake = FakeGenerator(details=[{'box_code': 'NOPE', 'amount': 1}])
        with (
            patch.object(L10nGaDeclarationGenerator, '_get', lambda registry, key: fake),
            self.assertRaisesRegex(UserError, 'NOPE'),
        ):
            declaration.action_compute()

    def test_payslip_generator_f16(self):
        slip = self._f16_slip()
        declaration = self._declaration()
        declaration.action_compute()
        values = {line.code: line.value_amount for line in declaration.line_ids if line.value_kind == 'amount'}
        self.assertEqual(values, {'B_IRPP': F16_IRPP, 'B_TCS': F16_TCS, 'B_FNH': F16_FNH, 'B_CNSS': F16_CNSS})
        self.assertEqual(declaration.amount_total, F16_IRPP + F16_TCS + F16_FNH)
        irpp = declaration.detail_ids.filtered(lambda d: d.box_id.code == 'B_IRPP')
        self.assertEqual((irpp.employee_id, irpp.label, irpp.amount), (slip.employee_id, 'F16', F16_IRPP))
        self.assertEqual(irpp.payslip_line_ids, self._line(slip, 'GA_IRPP'))
        self.assertEqual(len(declaration.detail_ids), 4)
        self.assertFalse(declaration.issue_ids)

    def test_payslip_generator_sums_employees_and_skips_drafts(self):
        self._f16_slip()
        self._f16_slip(self._f16_employee('Deuxième'))
        self._f16_slip(self._f16_employee('Brouillon'), validate=False)
        declaration = self._declaration()
        declaration.action_compute()
        self.assertEqual(self._box(declaration, 'B_IRPP').value_amount, 2 * F16_IRPP)
        self.assertEqual(len(declaration.detail_ids.employee_id), 2)
        self.assertNotIn('Brouillon', declaration.detail_ids.mapped('label'))

    def test_december_paid_in_january(self):
        self._f16_slip(period=DEC_2025, payment_date=date(2026, 1, 5))
        december = self._declaration(period=DEC_2025)
        january = self._declaration(period=JAN_2026)
        (december | january).action_compute()
        self.assertFalse(self._box(december, 'B_TCS').value_amount)
        self.assertTrue(self._box(january, 'B_TCS').value_amount)
        by_period = self._declaration_type('T_PERIOD', period_basis='period')
        december_period = self._declaration(decl_type=by_period, period=DEC_2025)
        december_period.action_compute()
        self.assertEqual(self._box(december_period, 'B_TCS').value_amount, self._box(january, 'B_TCS').value_amount)

    def test_multi_company(self):
        self._f16_slip()
        other = self.env['res.company'].create(
            {
                'name': 'Autre société Gabon',
                'country_id': self.env.ref('base.ga').id,
                'currency_id': self.company.currency_id.id,
            }
        )
        declaration = self._declaration(company=other)
        declaration.action_compute()
        self.assertFalse(declaration.detail_ids)
        self.assertFalse(declaration.amount_total)
