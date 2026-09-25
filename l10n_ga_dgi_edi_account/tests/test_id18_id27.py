import base64
import io
import zipfile
from datetime import date

from openpyxl import load_workbook

from odoo.fields import Command
from odoo.tests import tagged

from .common import SEPT, GaWithholdingCase


@tagged('post_install', '-at_install')
class TestId18Id27(GaWithholdingCase):
    """ID18 et ID27 mensuelles (base 07 §3 ; plan 5) : retenues lues sur les paiements du mois."""

    def _values(self, declaration):
        return {line.code: line._value() for line in declaration.line_ids}

    def test_id18_full_payment(self):
        bill = self._bill(self.provider, 100_000)
        payment = self._pay(bill)
        self.assertEqual(payment.withholding_line_ids.tax_id, self.ras_095)
        id18 = self._monthly('ID18')
        self.assertEqual(len(id18), 1, 'préparée à la validation du paiement (Observer)')
        values = self._values(id18)
        self.assertEqual((values['TOTAL_BASE'], values['TOTAL_WITHHELD']), (100_000, 9_500))
        self.assertEqual(id18.amount_total, 9_500)
        detail = id18.detail_ids
        self.assertEqual((detail.partner_id, detail.amount, detail.payload['nif']), (self.provider, 9_500, 'NIF-PREST'))
        self.assertIn(payment.name, detail.payload['payments'])
        if payment.move_id:  # sans compte d'attente, l'écriture n'existe qu'au rapprochement bancaire
            self.assertIn(payment.move_id, detail.move_line_ids.move_id)
        self.assertEqual(id18.due_date, date(2026, 10, 15))
        self.assertFalse(id18.issue_ids)

    def test_partial_and_two_payments(self):
        bill = self._bill(self.provider, 200_000)
        self._pay(bill, amount=120_000)
        self.assertEqual(self._values(self._monthly('ID18'))['TOTAL_BASE'], 120_000)
        self._pay(bill, day=date(2026, 9, 25), amount=80_000)
        values = self._values(self._monthly('ID18'))
        self.assertEqual((values['TOTAL_BASE'], values['TOTAL_WITHHELD']), (200_000, 19_000))
        self.assertIn(bill.payment_state, ('paid', 'in_payment'))  # « en cours » tant que non rapproché

    def test_refund(self):
        self._pay(self._bill(self.provider, 100_000))
        refund = self._bill(self.provider, 20_000, move_type='in_refund')
        self._pay(refund, day=date(2026, 9, 26))
        values = self._values(self._monthly('ID18'))
        self.assertEqual((values['TOTAL_BASE'], values['TOTAL_WITHHELD']), (80_000, 7_600))

    def test_id27_non_resident_only_20(self):
        self._pay(self._bill(self.foreigner, 200_000))
        id27 = self._monthly('ID27')
        values = self._values(id27)
        self.assertEqual((values['TOTAL_BASE'], values['TOTAL_WITHHELD']), (200_000, 40_000))
        self.assertEqual(id27.detail_ids.payload['country'], 'France')
        self.assertFalse(self._monthly('ID18').detail_ids, 'jamais 9,5 % pour un non-résident')
        self.assertFalse(id27.issue_ids, 'NIF non exigé d’un non-résident')

    def test_checks(self):
        no_nif = self._partner('Sans NIF', l10n_ga_vat_subject=False, vat=False)
        self._pay(self._bill(no_nif, 50_000))
        unclassified = self._partner('Non classé', l10n_ga_vat_subject=False, l10n_ga_fee_category=False, vat='N-U')
        bill = self._bill(unclassified, 30_000)
        bill.button_draft()
        bill.invoice_line_ids.tax_ids = self.ras_095
        bill.action_post()
        self._pay(bill)
        skipped = self._bill(self.provider, 40_000)
        wizard = (
            self.env['account.payment.register']
            .with_context(active_model='account.move', active_ids=skipped.ids)
            .create({'payment_date': date(2026, 9, 21)})
        )
        wizard.withholding_line_ids = [Command.clear()]  # retenue supprimée à la main
        self.assertFalse(wizard.should_withhold_tax)
        wizard._create_payments()
        id18 = self._monthly('ID18')
        id18.action_compute()
        codes = set(id18.issue_ids.mapped('code'))
        self.assertTrue({'GA_RAS_NO_NIF', 'GA_RAS_UNCLASSIFIED', 'GA_RAS_MISSING'} <= codes, codes)

    def test_template_filled(self):
        partners = [self.provider] + [
            self._partner(f'Prestataire {i:02d}', l10n_ga_vat_subject=False, vat=f'NIF-{i:02d}') for i in range(10)
        ]
        for partner in partners:
            self._pay(self._bill(partner, 10_000))
        id18 = self._monthly('ID18')
        id18.with_user(self.declarant).action_validate()
        xlsx = id18.snapshot_attachment_ids.filtered(lambda a: a.name.endswith('.xlsx'))
        content = base64.b64decode(xlsx.datas)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for name in archive.namelist():
                if name.startswith('xl/worksheets/'):
                    self.assertNotIn(b'<f>', archive.read(name), name)
        book = load_workbook(io.BytesIO(content))
        sheet = book['Bordereau']
        self.assertEqual([sheet[c].value for c in ('E12', 'L12', 'D16')], [2026, 9, 'NIF-TEST'])
        names = sorted(p.name for p in partners)
        self.assertEqual([sheet[f'B{r}'].value for r in (32, 41)], [names[0], names[9]])
        self.assertEqual((sheet['M32'].value, sheet['O32'].value), (10_000, 950))
        overflow = book['2- Listes ']
        self.assertEqual(overflow['B12'].value, names[10], '11e prestataire sur le feuillet supplémentaire')
        self.assertEqual((overflow['F51'].value, overflow['G51'].value), (10_000, 950))

    def test_multi_company(self):
        other = self.env['res.company'].create(
            {
                'name': 'Filiale Gabon',
                'country_id': self.env.ref('base.ga').id,
                'currency_id': self.company.currency_id.id,
            }
        )
        self.env.user.company_ids |= other
        self.env['account.chart.template'].try_loading('ga', other, install_demo=False)
        env = self.env(context=dict(self.env.context, allowed_company_ids=[other.id, self.company.id]))
        self.provider.invalidate_recordset()
        bill = self._bill(self.provider.with_env(env), 100_000, company=other)
        self.assertEqual(bill.invoice_line_ids.tax_ids.l10n_ga_withholding_kind, 'ras_095')
        self._pay(bill)
        self.assertFalse(self._monthly('ID18'))
        self.assertEqual(self._values(self._monthly('ID18', company=other))['TOTAL_WITHHELD'], 9_500)
        self.assertEqual(SEPT[0].month, 9)
