from odoo import models

from ..declaration_generator import WARNING

CFP_SECTION = 'cfp'


class L10nGaDeclarationGeneratorId10(models.AbstractModel):
    """ID10 : retenues sur salaires (IRPP, TCS, FNH) et, selon l'option société, CFP (base 06 §1).

    Les cases et leurs rubriques sont en données (``l10n_ga_declaration_type_data.xml``) ; ce générateur
    n'ajoute que les règles propres à l'imprimé.
    """

    _name = 'l10n_ga.declaration.generator.id10'
    _inherit = 'l10n_ga.declaration.generator.payslip'
    _description = 'ID10 — retenues sur salaires et CFP'

    def _blank_sections(self, declaration):
        # D-76 : la CFP n'est jamais déclarée deux fois ; cadre 3 vide si la société la déclare sur l'ID28.
        return {CFP_SECTION} if declaration.company_id.l10n_ga_cfp_declaration == 'id28' else set()

    def _checks(self, declaration, facts):
        return super()._checks(declaration, facts) + cfp_rounding_check(self, declaration, facts)


def cfp_rounding_check(generator, declaration, facts):
    """Base × taux ≈ Σ CFP des bulletins : l'écart d'arrondi ne dépasse pas 1 franc par salarié."""
    boxes = generator._boxes(declaration)
    base_box = boxes.filtered(lambda b: b.section == CFP_SECTION and b.source_measure == 'base')[:1]
    rate_box = boxes.filtered(lambda b: b.section == CFP_SECTION and b.parameter_code)[:1]
    amount_box = boxes.filtered(
        lambda b: b.section == CFP_SECTION and b.is_total and b.source_measure == 'total' and b._has_source()
    )[:1]
    if not (base_box and rate_box and amount_box):
        return []
    values = generator._fill(declaration, facts)
    base, rate, amount = (values.get(box.code) or 0.0 for box in (base_box, rate_box, amount_box))
    employees = {fact['employee'] for fact in facts}
    if abs(base * rate - amount) <= len(employees):
        return []
    message = declaration.env._(
        'CFP : base %(base)s × taux %(rate)s ≠ %(amount)s déclarés (écart supérieur aux arrondis par salarié).',
        base=base,
        rate=rate,
        amount=amount,
    )
    return [(WARNING, 'GA_DECL_CFP_ROUNDING', message, declaration)]
