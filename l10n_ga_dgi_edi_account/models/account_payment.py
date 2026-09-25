from odoo import models

MONTHLY_GENERATORS = ('id18', 'id27')


class AccountPayment(models.Model):
    """Observer (ADR-10) : un paiement validé met à jour l'ID18 / l'ID27 du mois de paiement."""

    _inherit = 'account.payment'

    def action_post(self):
        result = super().action_post()
        self._l10n_ga_notify_declarations()
        return result

    def _l10n_ga_notify_declarations(self):
        Declaration = self.env['l10n_ga.declaration']
        registry = self.env['l10n_ga.declaration.generator']
        types = Declaration._l10n_ga_auto_types().filtered(lambda t: t.generator_key in MONTHLY_GENERATORS)
        periods = set()
        for payment in self.filtered(lambda p: p.withholding_line_ids and p.date):
            for decl_type in types:
                if registry._get(decl_type.generator_key)._applies(payment.company_id) and decl_type._is_active_on(
                    payment.date
                ):
                    periods.add((payment.company_id, decl_type, *decl_type._period_bounds(payment.date)))
        for company, decl_type, date_from, date_to in sorted(periods, key=lambda p: (p[0].id, p[1].id, p[2])):
            Declaration._l10n_ga_prepare(company, decl_type, date_from, date_to)
