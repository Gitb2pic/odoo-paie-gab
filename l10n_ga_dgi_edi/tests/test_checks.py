from datetime import date
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from ..models.checks import COMMON_CHECKS
from ..models.declaration_generator import L10nGaDeclarationGenerator
from .common import FakeGenerator, GaDeclarationCase

EXISTING_PARAMETER = 'l10n_ga_smig_amount'


@tagged('post_install', '-at_install')
class TestDeclarationChecks(GaDeclarationCase):
    """Patron 8 (RG15, ADR-18) : chaîne COMMON_CHECKS, validation refusée si anomalie bloquante."""

    def _codes(self, declaration):
        return sorted(declaration.issue_ids.mapped('code'))

    def _with_fake(self, fake):
        return patch.object(L10nGaDeclarationGenerator, '_get', lambda registry, key: fake)

    def test_common_chain(self):
        self.assertEqual(
            [check.code for check in COMMON_CHECKS],
            ['GA_DECL_NO_CNSS', 'GA_DECL_DUPLICATE', 'GA_DECL_PARAM_MISSING', 'GA_DECL_TOTALS'],
        )

    def test_missing_cnss_blocks_validation(self):
        employee = self._f16_employee('Sans CNSS', ssnid=False)
        self._f16_slip(employee)
        declaration = self._declaration()
        declaration.action_compute()
        issue = declaration.issue_ids
        self.assertEqual(issue.code, 'GA_DECL_NO_CNSS')
        self.assertEqual(
            (issue.severity, issue.scope, issue.employee_id, issue.company_id),
            ('blocking', 'declaration', employee, self.company),
        )
        self.assertEqual((issue.res_model, issue.res_id), ('hr.employee', employee.id))
        self.assertEqual(declaration.blocking_count, 1)
        with self.assertRaisesRegex(UserError, 'n° CNSS absent'):
            declaration.with_user(self.declarant).action_validate()
        self.assertEqual(declaration.state, 'computed')
        employee.ssnid = 'CNSS-OK'
        declaration.action_compute()
        self.assertFalse(declaration.issue_ids)  # anomalies recréées à chaque calcul
        declaration.with_user(self.declarant).action_validate()
        self.assertEqual(declaration.state, 'validated')

    def test_duplicate_period(self):
        self._declaration(period=(date(2026, 9, 1), date(2026, 9, 15)))
        declaration = self._declaration()
        declaration.action_compute()
        self.assertEqual(self._codes(declaration), ['GA_DECL_DUPLICATE'])
        self.assertEqual(declaration.issue_ids.severity, 'blocking')

    def test_parameter_missing(self):
        fake = FakeGenerator(parameters=[EXISTING_PARAMETER, 'l10n_ga_parametre_inexistant'])
        with self._with_fake(fake):
            declaration = self._declaration()
            declaration.action_compute()
        self.assertEqual(self._codes(declaration), ['GA_DECL_PARAM_MISSING'])
        self.assertIn('l10n_ga_parametre_inexistant', declaration.issue_ids.message)

    def test_totals_match_details(self):
        employee = self._f16_employee('Détail')
        fake = FakeGenerator(
            values={'B_IRPP': 100, 'B_TCS': 50},
            details=[
                {'box_code': 'B_IRPP', 'employee_id': employee.id, 'label': employee.name, 'amount': 90},
                {'box_code': 'B_TCS', 'employee_id': employee.id, 'label': employee.name, 'amount': 50},
            ],
        )
        with self._with_fake(fake):
            declaration = self._declaration()
            declaration.action_compute()
        self.assertEqual(self._codes(declaration), ['GA_DECL_TOTALS'])
        self.assertIn('B_IRPP', declaration.issue_ids.message)

    def test_generator_issues_appended(self):
        fake = FakeGenerator(issues=[('warning', 'GA_TEST_WARN', 'Avertissement du générateur', self.company)])
        with self._with_fake(fake):
            declaration = self._declaration()
            declaration.action_compute()
            self.assertEqual(self._codes(declaration), ['GA_TEST_WARN'])
            self.assertEqual((declaration.blocking_count, declaration.warning_count), (0, 1))
            declaration.with_user(self.declarant).action_validate()  # un avertissement ne bloque pas
        self.assertEqual(declaration.state, 'validated')

    def test_issue_cascade_and_scope_selection(self):
        fake = FakeGenerator(issues=[('blocking', 'GA_TEST', 'Bloquant', self.company)])
        with self._with_fake(fake):
            declaration = self._declaration()
            declaration.action_compute()
        issue = declaration.issue_ids
        self.assertIn('declaration', dict(issue._fields['scope'].selection))
        self.assertEqual(issue.declaration_id, declaration)
        declaration.action_cancel()
        declaration.unlink()
        self.assertFalse(issue.exists())
