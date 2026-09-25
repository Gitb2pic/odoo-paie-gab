from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import GaWithholdingCase


@tagged('post_install', '-at_install')
class TestPartnerWithholding(GaWithholdingCase):
    """Classement des tiers (RG27), retenues au paiement, anti-double retenue (plan 5, D-95, D-96)."""

    def test_taxes_loaded_on_ga_chart(self):
        self.assertEqual((self.ras_095.amount, self.ras_20.amount), (-9.5, -20.0))
        for tax in self.ras_095 | self.ras_20:
            with self.subTest(tax=tax.name):
                self.assertTrue(tax.is_withholding_tax_on_payment)
                self.assertEqual(tax.type_tax_use, 'purchase')
                self.assertTrue(tax.withholding_sequence_id)
                account = tax.invoice_repartition_line_ids.filtered(lambda r: r.repartition_type == 'tax').account_id
                self.assertEqual(account.code[:4], '4478')
        before = self.env['account.tax'].search_count([('l10n_ga_withholding_kind', '!=', False)])
        self.env['account.chart.template']._l10n_ga_load_withholding(self.company)  # installation : idempotente
        self.assertEqual(self.env['account.tax'].search_count([('l10n_ga_withholding_kind', '!=', False)]), before)

    def test_partner_classification(self):
        self.assertEqual(self.provider.l10n_ga_withholding_kind, 'ras_095')
        self.assertEqual((self.foreigner.l10n_ga_withholding_kind, self.foreigner.l10n_ga_zone), ('ras_20', 'other'))
        cemac = self._partner('Cabinet Douala', l10n_ga_is_resident=False, country_id=self.env.ref('base.cm').id)
        self.assertEqual(cemac.l10n_ga_zone, 'cemac')
        vat_subject = self._partner('Assujetti', l10n_ga_vat_subject=True)
        landlord = self._partner('Bailleur', l10n_ga_vat_subject=False, l10n_ga_fee_category='rent')
        self.assertFalse(vat_subject.l10n_ga_withholding_kind)
        self.assertFalse(landlord.l10n_ga_withholding_kind, 'loyers : ID09, V2.0')

    def test_fiscal_position_follows_classification(self):
        position = self.provider.with_company(self.company).property_account_position_id
        self.assertEqual(position.l10n_ga_withholding_kind, 'ras_095')
        self.provider.l10n_ga_vat_subject = True
        self.assertFalse(self.provider.with_company(self.company).property_account_position_id)
        foreigner_position = self.foreigner.with_company(self.company).property_account_position_id
        self.assertEqual(foreigner_position.l10n_ga_withholding_kind, 'ras_20')

    def test_bill_lines_get_withholding(self):
        self.assertEqual(self._bill(self.provider, 100_000).invoice_line_ids.tax_ids, self.ras_095)
        self.assertEqual(self._bill(self.foreigner, 100_000).invoice_line_ids.tax_ids, self.ras_20)

    def test_no_double_withholding(self):
        bill = self._bill(self.provider, 100_000)
        bill.button_draft()
        with self.assertRaises(ValidationError):
            bill.invoice_line_ids.tax_ids = [Command.set((self.ras_095 | self.ras_20).ids)]
        foreign_bill = self._bill(self.foreigner, 100_000)
        foreign_bill.button_draft()
        with self.assertRaises(ValidationError):
            foreign_bill.invoice_line_ids.tax_ids = [Command.set(self.ras_095.ids)]  # non-résident : 20 % seul
