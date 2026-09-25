from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import GaDeclarationCase


@tagged('post_install', '-at_install')
class TestDeclarationSecurity(GaDeclarationCase):
    """Groupes et règles multi-société (règle d'or 11)."""

    def test_groups_hierarchy(self):
        self.assertTrue(self.declarant.has_group('hr_payroll.group_hr_payroll_user'))
        self.assertTrue(self.manager.has_group('l10n_ga_dgi_edi.group_l10n_ga_declarant'))
        self.assertFalse(self.payroll_user.has_group('l10n_ga_dgi_edi.group_l10n_ga_declarant'))
        self.assertTrue(self.env.ref('base.user_admin').has_group('l10n_ga_dgi_edi.group_l10n_ga_declaration_manager'))

    def test_multi_company_rules(self):
        self._f16_slip()
        declaration = self._declaration()
        declaration.action_compute()
        other = self.env['res.company'].create({'name': 'Autre société', 'country_id': self.env.ref('base.ga').id})
        outsider = self._user('ga_decl_outsider', 'l10n_ga_dgi_edi.group_l10n_ga_declarant', company=other)
        env = self.env(user=outsider, context={'allowed_company_ids': other.ids})
        for model in ('l10n_ga.declaration', 'l10n_ga.declaration.line', 'l10n_ga.declaration.detail'):
            with self.subTest(model=model):
                self.assertFalse(env[model].search([('company_id', '=', self.company.id)]))
        self.assertFalse(env['l10n_ga.check.issue'].search([('declaration_id', '=', declaration.id)]))
        own = self.env(user=self.declarant)['l10n_ga.declaration'].search([('id', '=', declaration.id)])
        self.assertEqual(own, declaration)
        self.assertTrue(own.line_ids and own.detail_ids)

    def test_type_configuration_rights(self):
        with self.assertRaises(AccessError):
            self.decl_type.with_user(self.declarant).name = 'Modifié'
        self.decl_type.with_user(self.manager).name = 'Modifié'
        self.assertEqual(self.decl_type.name, 'Modifié')
        self.assertTrue(self.decl_type.with_user(self.payroll_user).box_ids)
