from odoo import api, models
from odoo.exceptions import ValidationError


def check_withholding(partner, kinds, env):
    """Anti-double retenue (RG27) : jamais 9,5 % et 20 % ensemble ; jamais 9,5 % pour un non-résident."""
    kinds = set(kinds) - {False}
    if len(kinds) > 1:
        raise ValidationError(env._('Une retenue de 9,5 % et une retenue de 20 % ne se cumulent jamais.'))
    if 'ras_095' in kinds and partner and not partner.commercial_partner_id.l10n_ga_is_resident:
        raise ValidationError(
            env._(
                '%(partner)s est non-résident : seule la retenue de 20 %% s’applique, jamais celle de 9,5 %%.',
                partner=partner.display_name,
            )
        )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_computed_taxes(self):
        """Factures fournisseurs : la retenue gabonaise suit la position fiscale du document (D-96)."""
        taxes = super()._get_computed_taxes()
        move = self.move_id
        if not move.is_purchase_document(include_receipts=True) or not self.company_id:
            return taxes
        Tax = self.env['account.tax']
        withholding = Tax._l10n_ga_withholding_taxes(self.company_id)
        taxes = (taxes or Tax) - withholding
        kind = move.fiscal_position_id.l10n_ga_withholding_kind
        if kind:
            taxes |= withholding.filtered(lambda t: t.l10n_ga_withholding_kind == kind and t.active)[:1]
        return taxes

    @api.constrains('tax_ids', 'partner_id')
    def _check_l10n_ga_withholding(self):
        for line in self.filtered(lambda aml: aml.move_id.is_purchase_document(include_receipts=True)):
            check_withholding(line.move_id.partner_id, line.tax_ids.mapped('l10n_ga_withholding_kind'), line.env)
