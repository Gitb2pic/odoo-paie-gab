from datetime import date

from odoo.tests import tagged

from .common import F16_IRPP, SEPT, GaDeclarationCase

ACTIVITY_DUE = 'l10n_ga_dgi_edi.mail_activity_type_declaration_due'
ACTIVITY_FIX = 'l10n_ga_dgi_edi.mail_activity_type_declaration_fix'


@tagged('post_install', '-at_install')
class TestObserverCron(GaDeclarationCase):
    """Patron 11 (ADR-10, ADR-19) : validation des bulletins et cron J-10 préparent les déclarations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auto_type = cls._declaration_type('T_AUTO', auto_create=True)
        cls.company.l10n_ga_declarant_id = cls.declarant

    def _declarations(self, period=SEPT):
        return self.env['l10n_ga.declaration'].search(
            [('type_id', '=', self.auto_type.id), ('date_from', '=', period[0]), ('date_to', '=', period[1])]
        )

    def test_payslip_validation_prepares_declaration(self):
        self.assertFalse(self._declarations())
        self._f16_slip()
        declaration = self._declarations()
        self.assertEqual(len(declaration), 1)
        self.assertEqual(declaration.state, 'computed')
        self.assertEqual(self._box(declaration, 'B_IRPP').value_amount, F16_IRPP)
        self.assertFalse(self.env['l10n_ga.declaration'].search([('type_id', '=', self.decl_type.id)]))

        second = self._f16_slip(self._f16_employee('Deuxième'))
        self.assertEqual(self._declarations(), declaration)
        self.assertEqual(self._box(declaration, 'B_IRPP').value_amount, 2 * F16_IRPP)

        second.action_payslip_paid()
        self.assertEqual(self._box(declaration, 'B_IRPP').value_amount, 2 * F16_IRPP)
        second.action_payslip_draft()  # bulletin remis en brouillon : sorti de la déclaration
        self.assertEqual(self._box(declaration, 'B_IRPP').value_amount, F16_IRPP)

    def test_payment_date_selects_period(self):
        self._f16_slip(payment_date=date(2026, 10, 5))
        self.assertFalse(self._declarations())
        self.assertEqual(len(self._declarations((date(2026, 10, 1), date(2026, 10, 31)))), 1)

    def test_validated_declaration_never_recomputed(self):
        self._f16_slip()
        declaration = self._declarations()
        declaration.with_user(self.declarant).action_validate()
        sha = declaration.sha256
        self._f16_slip(self._f16_employee('Tardif'))
        self.assertEqual(self._declarations(), declaration)
        self.assertEqual(self._box(declaration, 'B_IRPP').value_amount, F16_IRPP)
        self.assertEqual(declaration.sha256, sha)
        self.assertIn('rectificative', declaration.message_ids[:1].body)

    def test_inactive_type_ignored(self):
        self.auto_type.active_from = date(2026, 10, 1)
        self._f16_slip()
        self.assertFalse(self._declarations())

    def test_cron_prepares_due_declarations(self):
        self._f16_slip()
        Declaration = self.env['l10n_ga.declaration']
        Declaration._cron_prepare_due_declarations(today=date(2026, 9, 20))
        declaration = self._declarations()
        self.assertFalse(declaration.activity_ids, 'échéance du 15/10 hors de la fenêtre J-10')
        Declaration._cron_prepare_due_declarations(today=date(2026, 10, 6))
        activity = declaration.activity_ids
        self.assertEqual(activity.activity_type_id, self.env.ref(ACTIVITY_DUE))
        self.assertEqual((activity.user_id, activity.date_deadline), (self.declarant, date(2026, 10, 15)))
        Declaration._cron_prepare_due_declarations(today=date(2026, 10, 7))
        self.assertEqual(len(declaration.activity_ids), 1, 'pas de doublon')
        declaration.with_user(self.declarant).action_validate()
        declaration.with_user(self.declarant).action_mark_filed()
        self.assertFalse(declaration.activity_ids, 'activité soldée au dépôt')

    def test_cron_creates_missing_declaration_and_fix_activity(self):
        self._f16_slip(self._f16_employee('Sans CNSS', ssnid=False), validate=False)
        self.assertFalse(self._declarations())
        self.env['l10n_ga.declaration']._cron_prepare_due_declarations(today=date(2026, 10, 10))
        declaration = self._declarations()
        self.assertEqual(declaration.state, 'computed')
        self.assertFalse(declaration.issue_ids)  # bulletin brouillon : rien à déclarer
        self.env['hr.payslip'].search([('employee_id.name', '=', 'Sans CNSS')]).action_payslip_done()
        self.assertEqual(declaration.blocking_count, 1)
        self.env['l10n_ga.declaration']._cron_prepare_due_declarations(today=date(2026, 10, 10))
        types = declaration.activity_ids.activity_type_id
        self.assertEqual(types, self.env.ref(ACTIVITY_DUE) | self.env.ref(ACTIVITY_FIX))
        employee = declaration.issue_ids.employee_id
        employee.ssnid = 'CNSS-OK'
        declaration.action_compute()
        self.assertEqual(declaration.activity_ids.activity_type_id, self.env.ref(ACTIVITY_DUE))

    def test_declarant_fallback(self):
        self.company.l10n_ga_declarant_id = False
        declaration = self._declaration(decl_type=self.auto_type)
        self.assertEqual(declaration._l10n_ga_declarant(), self.declarant)  # premier membre du groupe (D-72)
        self.company.l10n_ga_declarant_id = self.manager
        self.assertEqual(declaration._l10n_ga_declarant(), self.manager)

    def test_no_declarant_posts_message(self):
        lonely = self.env['res.company'].create(
            {'name': 'Société sans déclarant', 'country_id': self.env.ref('base.ga').id}
        )
        declaration = self._declaration(decl_type=self.auto_type, company=lonely)
        declaration._l10n_ga_schedule_activities()
        self.assertFalse(declaration.activity_ids)
        self.assertIn('déclarant', declaration.message_ids[:1].body)

    def test_cron_record(self):
        cron = self.env.ref('l10n_ga_dgi_edi.ir_cron_l10n_ga_declaration_schedule')
        self.assertEqual((cron.interval_number, cron.interval_type), (1, 'days'))
        self.assertIn('_cron_prepare_due_declarations', cron.code)
