from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import GaPayrollCase


@tagged('post_install', '-at_install')
class TestTaxParts(GaPayrollCase):
    """RG03 : parts calculées et stockées sur la version, forçage motivé (ADR-05)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls._employee('Parts', 300_000, start=date(2026, 1, 1))
        cls.version = cls.employee.version_id

    def _parts(self, **values):
        self.version.write(values)
        return self.version.l10n_ga_tax_parts

    def test_parts_by_family_situation(self):
        cases = [
            ({'marital': 'single', 'children': 0}, 1.0),
            ({'marital': 'single', 'children': 2}, 2.5),
            ({'marital': 'married', 'children': 0}, 2.0),
            ({'marital': 'married', 'children': 3}, 3.5),
            ({'marital': 'widower', 'children': 1}, 2.5),
            ({'marital': 'divorced', 'children': 0}, 1.0),
            ({'marital': 'cohabitant', 'children': 1}, 2.0),
            ({'marital': 'married', 'children': 8}, 5.0),  # 6 enfants au plus
        ]
        for values, expected in cases:
            with self.subTest(**values):
                self.assertEqual(self._parts(**values), expected)

    def test_disabled_children_and_extra_half_part(self):
        self.assertEqual(self._parts(marital='married', children=2, l10n_ga_disabled_children=1), 3.5)
        self.assertEqual(
            self._parts(marital='single', children=0, l10n_ga_disabled_children=0, l10n_ga_extra_half_part=True), 1.5
        )

    def test_forced_parts_with_reason(self):
        parts = self._parts(
            marital='single', children=0, l10n_ga_tax_parts_forced=4.5, l10n_ga_tax_parts_forced_reason='Jugement'
        )
        self.assertEqual(parts, 4.5)
        self.assertEqual(self.employee.l10n_ga_tax_parts, 4.5)  # exposé sur le salarié (related)

    def test_forced_parts_rejected(self):
        for value in (0.5, 7.0, 2.3):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.version.write({'l10n_ga_tax_parts_forced': value, 'l10n_ga_tax_parts_forced_reason': 'x'})
        with self.assertRaisesRegex(ValidationError, 'motif'):
            self.version.write({'l10n_ga_tax_parts_forced': 2.0, 'l10n_ga_tax_parts_forced_reason': ' '})

    def test_disabled_children_bounded_by_children(self):
        with self.assertRaisesRegex(ValidationError, 'infirmes'):
            self.version.write({'children': 1, 'l10n_ga_disabled_children': 2})
        with self.assertRaises(ValidationError):
            self.version.write({'l10n_ga_disabled_children': -1})

    def test_employee_has_no_stored_ga_field(self):
        stored = [
            name
            for name, field in self.env['hr.employee']._fields.items()
            if name.startswith('l10n_ga_') and field.store and not field.inherited
        ]
        self.assertFalse(stored, 'règle d’or 5 : données fiscales sur hr.version')
