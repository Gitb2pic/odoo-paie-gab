from psycopg2 import IntegrityError  # pylint: disable=import-error

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import F16_CFP, F16_FNH, F16_IRPP, F16_TCS, GaDeclarationCase

TOTAL = F16_IRPP + F16_TCS + F16_FNH + F16_CFP


@tagged('post_install', '-at_install')
class TestPayments(GaDeclarationCase):
    """Quittances multiples (F11, RG16, D-78)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._f16_slip()
        cls.declaration = cls._find(cls._type('ID10'))

    def setUp(self):
        super().setUp()
        self.decl = self.declaration.with_user(self.declarant)
        self.decl.action_validate()

    def _pay(self, amount, kind='rs', number=None):
        return (
            self.env['l10n_ga.declaration.payment']
            .with_user(self.declarant)
            .create(
                {
                    'declaration_id': self.decl.id,
                    'amount': amount,
                    'kind': kind,
                    'receipt_number': number or f'Q-{kind}-{amount}',
                }
            )
        )

    def test_two_receipts_make_it_paid(self):
        self.assertEqual(self.decl.amount_total, TOTAL)
        self.decl.action_mark_filed()
        self._pay(F16_IRPP + F16_TCS, 'rs')
        self.assertEqual(self.decl.state, 'filed')
        self.assertEqual(self.decl.amount_residual, F16_FNH + F16_CFP)
        self._pay(F16_FNH + F16_CFP, 'fnh')
        self.assertEqual(self.decl.state, 'paid')
        self.assertEqual((self.decl.amount_paid, self.decl.amount_residual), (TOTAL, 0))
        self.assertFalse(self.decl.issue_ids)

    def test_partial_payment_stays_filed(self):
        self.decl.action_mark_filed()
        self._pay(1_000)
        self.assertEqual(self.decl.state, 'filed')
        with self.assertRaises(UserError):
            self.decl.action_mark_paid()

    def test_overpayment_flagged(self):
        self.decl.action_mark_filed()
        payment = self._pay(TOTAL + 500)
        self.assertEqual(self.decl.state, 'paid')
        issue = self.decl.issue_ids
        self.assertEqual((issue.code, issue.severity), ('GA_DECL_OVERPAID', 'warning'))
        self.assertIn('Sur-paiement', self.decl.message_ids[:1].body)
        payment.amount = TOTAL
        self.assertFalse(self.decl.issue_ids)
        self.assertEqual(self.decl.state, 'paid')

    def test_removed_receipt_back_to_filed(self):
        self.decl.action_mark_filed()
        payment = self._pay(TOTAL)
        self.assertEqual(self.decl.state, 'paid')
        payment.unlink()
        self.assertEqual(self.decl.state, 'filed')

    def test_paid_before_filing(self):
        self._pay(TOTAL)
        self.assertEqual(self.decl.state, 'validated')
        with self.assertRaises(UserError):
            self.decl.action_unvalidate()  # quittances à retirer d'abord
        self.decl.action_mark_filed()
        self.assertEqual(self.decl.state, 'paid')

    def test_payment_rules(self):
        draft = self._declaration()
        with self.assertRaises(UserError):
            self.env['l10n_ga.declaration.payment'].with_user(self.declarant).create(
                {'declaration_id': draft.id, 'amount': 10, 'receipt_number': 'X'}
            )
        with self.assertRaises(AccessError):
            self.env['l10n_ga.declaration.payment'].with_user(self.payroll_user).create(
                {'declaration_id': self.decl.id, 'amount': 10, 'receipt_number': 'X'}
            )
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), self.cr.savepoint():
            self._pay(-5)
        payment = self._pay(10)
        self.assertEqual(payment.company_id, self.company)
        self.assertTrue(payment.with_user(self.payroll_user).read(['amount']))

    def test_multi_company_rule(self):
        payment = self._pay(10)
        other = self.env['res.company'].create({'name': 'Autre société', 'country_id': self.env.ref('base.ga').id})
        outsider = self._user('ga_pay_outsider', 'l10n_ga_dgi_edi.group_l10n_ga_declarant', company=other)
        env = self.env(user=outsider, context={'allowed_company_ids': other.ids})
        self.assertFalse(env['l10n_ga.declaration.payment'].search([('id', '=', payment.id)]))
