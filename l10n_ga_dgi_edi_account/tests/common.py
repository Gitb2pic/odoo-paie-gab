"""Société au plan « ga » (retenues chargées), tiers classés, factures fournisseurs et paiements."""

from datetime import date

from odoo.addons.l10n_ga_dgi_edi.tests.common import GaDeclarationCase
from odoo.fields import Command

SEPT = (date(2026, 9, 1), date(2026, 9, 30))
YEAR = (date(2026, 1, 1), date(2026, 12, 31))


class GaWithholdingCase(GaDeclarationCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['account.chart.template'].try_loading('ga', cls.company, install_demo=False)
        cls.ras_095, cls.ras_20 = (
            cls.env['account.tax']._l10n_ga_withholding_taxes(cls.company, kind) for kind in ('ras_095', 'ras_20')
        )
        cls.product = cls.env['product.product'].create(
            {'name': 'Prestation de services', 'type': 'service', 'supplier_taxes_id': [Command.clear()]}
        )
        cls.provider = cls._partner('Prestataire local', vat='NIF-PREST', l10n_ga_vat_subject=False)
        cls.foreigner = cls._partner(
            'Consultant Paris', l10n_ga_is_resident=False, country_id=cls.env.ref('base.fr').id, vat=False
        )

    @classmethod
    def _partner(cls, name, **values):
        values.setdefault('l10n_ga_fee_category', 'service')
        values.setdefault('country_id', cls.env.ref('base.ga').id)
        return cls.env['res.partner'].create({'name': name, 'is_company': True, **values})

    @classmethod
    def _bill(cls, partner, amount, day=date(2026, 9, 5), move_type='in_invoice', company=None):
        bill = cls.env['account.move'].create(
            {
                'move_type': move_type,
                'partner_id': partner.id,
                'company_id': (company or cls.company).id,
                'invoice_date': day,
                'date': day,
                'invoice_line_ids': [Command.create({'product_id': cls.product.id, 'price_unit': amount})],
            }
        )
        bill.action_post()
        return bill

    @classmethod
    def _pay(cls, moves, day=date(2026, 9, 20), amount=None):
        values = {'payment_date': day}
        if amount:
            values['amount'] = amount
        wizard = (
            cls.env['account.payment.register']
            .with_context(active_model='account.move', active_ids=moves.ids)
            .create(values)
        )
        return wizard._create_payments()

    def _monthly(self, code, period=SEPT, company=None):
        return self._find(self._type_account(code), period, company)

    @classmethod
    def _type_account(cls, code):
        return cls.env.ref(f'l10n_ga_dgi_edi_account.declaration_type_{code.lower()}')
