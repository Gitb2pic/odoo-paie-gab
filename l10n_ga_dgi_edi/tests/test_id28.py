import base64
import io

from openpyxl import load_workbook

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import F16_CFP, F16_CNSS, F16_SOCIAL_BASE, SEPT, GaDeclarationCase


@tagged('post_install', '-at_install')
class TestId28(GaDeclarationCase):
    """ID28 (base 06 §2, D-76) : CFP déclarée une seule fois, sur l'ID10 ou sur l'ID28."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.id10, cls.id28 = cls._type('ID10'), cls._type('ID28')

    def test_prepared_only_when_company_chooses_id28(self):
        self.assertEqual(self.company.l10n_ga_cfp_declaration, 'id10')
        self._f16_slip()
        self.assertFalse(self._find(self.id28))
        self.env['l10n_ga.declaration']._cron_prepare_due_declarations(today=SEPT[1].replace(month=10, day=6))
        self.assertFalse(self._find(self.id28), 'le cron ne prépare pas non plus l’ID28')

    def test_manual_id28_blocked_when_cfp_on_id10(self):
        self._f16_slip()
        declaration = self._declaration(decl_type=self.id28)
        declaration.action_compute()
        self.assertIn('GA_ID28_CFP_ON_ID10', declaration.issue_ids.mapped('code'))
        with self.assertRaises(UserError):
            declaration.with_user(self.declarant).action_validate()

    def test_cfp_declared_once_on_id28(self):
        self.company.l10n_ga_cfp_declaration = 'id28'
        self._f16_slip()
        id28 = self._find(self.id28)
        values = self._values(id28)
        self.assertEqual(values['L1'] + values['L2'] + values['L4'], F16_SOCIAL_BASE)
        self.assertEqual(
            (values['L3'], values['L5'], values['L6'], values['L7']), (F16_CNSS, F16_SOCIAL_BASE, 0.005, F16_CFP)
        )
        self.assertEqual(id28.amount_total, F16_CFP)
        self.assertFalse(id28.issue_ids)
        id10 = self._find(self.id10)
        self.assertIsNone(self._values(id10)['R56'])
        cfp_total = id28.amount_total + (self._values(id10)['R56'] or 0)
        self.assertEqual(cfp_total, F16_CFP, 'CFP déclarée une seule fois')

        id28.with_user(self.declarant).action_validate()
        xlsx = id28.snapshot_attachment_ids.filtered(lambda a: a.name.endswith('.xlsx'))
        sheet = load_workbook(io.BytesIO(base64.b64decode(xlsx.datas)))['CFP']
        self.assertEqual(
            [sheet[cell].value for cell in ('H14', 'N14', 'D17', 'N30', 'Q41', 'Q42', 'Q43')],
            [2026, 9, 'NIF-TEST', 'LBV-01', F16_SOCIAL_BASE, 0.005, F16_CFP],
        )
        self.assertEqual(sheet['C37'].value, 'Salaires de base')
