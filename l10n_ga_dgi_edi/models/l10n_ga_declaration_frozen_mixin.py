from odoo import api, models
from odoo.exceptions import UserError

FROZEN_STATES = ('validated', 'filed', 'paid')


class L10nGaDeclarationFrozenMixin(models.AbstractModel):
    """Verrou de l'instantané (RG14, ADR-06) : les valeurs d'une déclaration validée ne bougent plus."""

    _name = 'l10n_ga.declaration.frozen.mixin'
    _description = 'Valeur figée de déclaration (Gabon)'

    def _check_not_frozen(self):
        if self.env.context.get('l10n_ga_declaration_engine'):
            return
        frozen = self.declaration_id.filtered(lambda d: d.state in FROZEN_STATES)
        if frozen:
            raise UserError(
                self.env._(
                    'La déclaration %(name)s est validée : ses valeurs sont figées. '
                    'Créez une déclaration rectificative.',
                    name=frozen[0].name,
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_not_frozen()
        return records

    def write(self, vals):
        self._check_not_frozen()
        return super().write(vals)

    def unlink(self):
        self._check_not_frozen()
        return super().unlink()
