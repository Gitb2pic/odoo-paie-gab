from collections import Counter

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..lib.ga_fiscal_core.exemptions import SOCIAL_CAPS, TAX_CAPS
from ..lib.ga_fiscal_core.treatment import DAS_COLUMNS, SOCIAL_BASES, TAX_BASES
from ..models.hr_salary_rule import DAS_COLUMN_SELECTION, SOCIAL_BASE_SELECTION, TAX_BASE_SELECTION


@tagged('post_install', '-at_install')
class TestRuleCodesUnique(TransactionCase):
    """RG22, défaut B1 (NET unique), F6 (traitement de chaque rubrique), ADR-17 (groupes connus)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.structure = cls.env.ref('l10n_ga_hr_payroll.structure_ga_employee')
        cls.ga_structures = cls.env['hr.payroll.structure'].search([('country_id.code', '=', 'GA')])

    def test_codes_unique_per_structure(self):
        self.assertIn(self.structure, self.ga_structures)
        for structure in self.ga_structures:
            duplicates = [code for code, count in Counter(structure.rule_ids.mapped('code')).items() if count > 1]
            self.assertFalse(duplicates, f'codes en double dans {structure.name} : {duplicates}')

    def test_single_net_rule(self):
        net_rules = self.structure.rule_ids.filtered(lambda r: r.code == 'NET')
        self.assertEqual(len(net_rules), 1)
        self.assertEqual(net_rules.category_id, self.env.ref('hr_payroll.NET'))
        self.assertEqual(len(self.structure.rule_ids.filtered(lambda r: r.category_id.code == 'NET')), 1)

    def test_default_structure_rules_not_copied(self):
        codes = set(self.structure.rule_ids.mapped('code'))
        self.assertFalse(codes & {'DEDUCTION', 'ATTACH_SALARY', 'ASSIG_SALARY', 'CHILD_SUPPORT', 'REIMBURSEMENT'})
        self.assertTrue({'BASIC', 'GROSS', 'NET'} <= codes)

    def test_every_rule_has_social_and_tax_treatment(self):
        rules = self.structure.rule_ids
        self.assertGreaterEqual(len(rules), 55)
        for rule in rules:
            self.assertTrue(rule.l10n_ga_social_base, rule.code)
            self.assertTrue(rule.l10n_ga_tax_base, rule.code)
            self.assertTrue(rule.l10n_ga_das_column, rule.code)

    def test_cap_groups_known_by_core_registry(self):
        for rule in self.structure.rule_ids:
            if rule.l10n_ga_social_cap_group:
                self.assertIn(rule.l10n_ga_social_cap_group, SOCIAL_CAPS, rule.code)
            if rule.l10n_ga_tax_cap_group:
                self.assertIn(rule.l10n_ga_tax_cap_group, TAX_CAPS, rule.code)

    def test_selection_keys_match_core_vocabulary(self):
        self.assertEqual(tuple(k for k, _ in SOCIAL_BASE_SELECTION), SOCIAL_BASES)
        self.assertEqual(tuple(k for k, _ in TAX_BASE_SELECTION), TAX_BASES)
        self.assertEqual(tuple(k for k, _ in DAS_COLUMN_SELECTION), DAS_COLUMNS)

    def _new_rule(self, **values):
        return self.env['hr.salary.rule'].create(
            {
                'name': 'Test',
                'code': 'GA_TEST',
                'struct_id': self.structure.id,
                'category_id': self.env.ref('hr_payroll.ALW').id,
                **values,
            }
        )

    def test_constraint_rejects_unknown_group(self):
        with self.assertRaisesRegex(ValidationError, 'inconnu'):
            self._new_rule(l10n_ga_social_base='subject', l10n_ga_tax_base='capped', l10n_ga_tax_cap_group='NOPE')

    def test_constraint_rejects_capped_without_group(self):
        with self.assertRaisesRegex(ValidationError, 'groupe'):
            self._new_rule(l10n_ga_social_base='capped', l10n_ga_tax_base='taxable')

    def test_constraint_accepts_valid_treatment_and_foreign_rules(self):
        rule = self._new_rule(
            l10n_ga_social_base='capped',
            l10n_ga_social_cap_group='TRANSPORT_35K',
            l10n_ga_tax_base='capped',
            l10n_ga_tax_cap_group='TRANSPORT_DAILY',
        )
        self.assertEqual(rule.l10n_ga_tax_cap_group, 'TRANSPORT_DAILY')
        foreign = self._new_rule(code='OTHER')  # règle sans traitement Gabon : non contrôlée
        self.assertFalse(foreign.l10n_ga_social_base)

    def test_core_rules_in_one_line(self):
        core_rules = self.structure.rule_ids.filtered('l10n_ga_core_value')
        self.assertGreaterEqual(len(core_rules), 16)
        for rule in core_rules:
            self.assertEqual(len(rule.amount_python_compute.strip().splitlines()), 1, rule.code)
            self.assertIn(f"payslip._l10n_ga_compute('{rule.l10n_ga_core_value}'", rule.amount_python_compute)
        deductions = core_rules.filtered(lambda r: r.category_id.parent_id == self.env.ref('hr_payroll.DED'))
        self.assertTrue(all(r.amount_python_compute.startswith('result = -') for r in deductions))
