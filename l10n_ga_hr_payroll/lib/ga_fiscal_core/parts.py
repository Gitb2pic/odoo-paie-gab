"""Quotient familial : nombre de parts fiscales (CGI art. 170-173, RG03).

Situations = codes ``marital`` de ``hr.version`` : single, married, cohabitant,
widower, divorced. Le concubinage n'est pas un mariage fiscal (traité comme single).
Toutes les valeurs de parts viennent de ``FiscalParams`` (règle d'or 1).
"""

MARITAL_CODES = ('single', 'married', 'cohabitant', 'widower', 'divorced')
PART_STEP = 0.5  # granularité d'un nombre de parts (demi-part), contrôle de saisie


def tax_parts(marital, children, disabled_children=0, extra_half_part=False, forced=None, *, p):
    """Nombre de parts pour l'IRPP (valeurs 2026 entre parenthèses).

    - marié, ou veuf avec enfants : base marié (2) + par enfant (0,5) ;
    - célibataire, divorcé, veuf sans enfant : base (1) ; avec n enfants :
      base + premier enfant (1) + par enfant suivant (0,5) × (n − 1) ;
    - ``p.max_children`` enfants au plus (6) ;
    - enfant infirme : supplément (0,5) chacun, dans la limite des enfants comptés ;
    - ``extra_half_part`` : parts spéciales (1,5) d'une personne seule **sans enfant à
      charge** ayant élevé des enfants, perdu un enfant de 16 ans ou plus, ou invalide ;
    - ``forced`` : parts forcées (de 1 à 6,5 par demi-part), prioritaires.
    """
    if forced is not None:
        if not p.forced_parts_min <= forced <= p.forced_parts_max or (forced / PART_STEP) % 1:
            raise ValueError(
                f'Nombre de parts forcé invalide : {forced} ({p.forced_parts_min} à {p.forced_parts_max} par demi-part)'
            )
        return float(forced)
    if marital not in MARITAL_CODES:
        raise ValueError(f'Situation familiale inconnue : {marital!r}')
    if children < 0 or disabled_children < 0:
        raise ValueError(f"Nombre d'enfants négatif : {children}, infirmes {disabled_children}")

    counted = min(children, p.max_children)
    disabled = min(disabled_children, counted)
    if marital == 'married' or (marital == 'widower' and counted):
        parts = p.parts_married + p.parts_married_per_child * counted
    elif counted:
        parts = p.parts_single + p.parts_single_first_child + p.parts_single_per_extra_child * (counted - 1)
    else:
        parts = p.parts_single_extra if extra_half_part else p.parts_single
    return parts + p.parts_disabled_child * disabled
