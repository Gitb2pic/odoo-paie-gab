"""Lecture des paiements fournisseurs validés (source unique des ID18, ID27, ID23, ID24, ID26).

En Odoo 19, un paiement dont le moyen n'a pas de compte d'attente reste « en cours » **sans écriture**
jusqu'au rapprochement bancaire ; ses lignes de retenue (``account.payment.withholding.line``) et ses
factures (``invoice_ids``) existent dès la validation. On lit donc les paiements, pas les écritures :
retenue et base en devise société, signe négatif pour un remboursement d'avoir (paiement entrant).
"""

from collections import defaultdict

VALID_STATES = ('in_process', 'paid')


def _sign(payment):
    return 1 if payment.payment_type == 'outbound' else -1


def _company_amount(payment, amount):
    company = payment.company_id
    if payment.currency_id == company.currency_id:
        return amount
    return payment.currency_id._convert(amount, company.currency_id, company, payment.date)


def supplier_payments(env, company, date_from, date_to, extra_domain=()):
    return env['account.payment'].search(
        [
            ('company_id', '=', company.id),
            ('state', 'in', VALID_STATES),
            ('partner_type', '=', 'supplier'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            *extra_domain,
        ]
    )


def withholding_by_partner(env, company, date_from, date_to, taxes):
    """``{tiers: {'base', 'withheld', 'lines', 'payments'}}`` des retenues ``taxes`` de la période."""
    result = defaultdict(
        lambda: {
            'base': 0.0,
            'withheld': 0.0,
            'lines': env['account.move.line'],
            'payments': env['account.payment'],
        }
    )
    payments = supplier_payments(env, company, date_from, date_to, [('withholding_line_ids.tax_id', 'in', taxes.ids)])
    for payment in payments:
        item = result[payment.partner_id.commercial_partner_id]
        for line in payment.withholding_line_ids.filtered(lambda w: w.tax_id in taxes):
            item['base'] += _sign(payment) * _company_amount(payment, line.base_amount)
            item['withheld'] += _sign(payment) * _company_amount(payment, line.amount)
        item['payments'] |= payment
        item['lines'] |= payment.move_id.line_ids.filtered(lambda aml: aml.tax_line_id in taxes or aml.tax_ids & taxes)
    return result


def settled_ht_by_partner(env, company, date_from, date_to, partners):
    """Sommes versées (HT) de la période (D-97) : montant réglé par chaque paiement, réparti entre ses
    factures au prorata de leur total, puis ramené au hors-taxes de chaque facture."""
    result = defaultdict(lambda: [0.0, env['account.move.line']])
    payments = supplier_payments(
        env, company, date_from, date_to, [('partner_id.commercial_partner_id', 'in', partners.ids)]
    )
    for payment in payments:
        bills = (payment.invoice_ids | payment.reconciled_bill_ids).filtered(
            lambda m: m.move_type in ('in_invoice', 'in_refund') and m.state == 'posted'
        )
        total = sum(abs(bill.amount_total_signed) for bill in bills)
        if not total:
            continue
        settled = _company_amount(payment, payment.amount)
        for bill in bills:
            share = settled * abs(bill.amount_total_signed) / total
            ht = share * abs(bill.amount_untaxed_signed) / abs(bill.amount_total_signed)
            item = result[bill.commercial_partner_id]
            item[0] += _sign(payment) * ht
            item[1] |= bill.line_ids.filtered(lambda aml: aml.account_id.account_type == 'liability_payable')
    return result
