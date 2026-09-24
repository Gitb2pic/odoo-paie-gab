"""Quotient familial : nombre de parts fiscales (CGI art. 170-173, RG03).

Situations = codes ``marital`` de ``hr.version`` : single, married, cohabitant,
widower, divorced. Le concubinage n'est pas un mariage fiscal (traité comme single).
"""

MARITAL_CODES = ('single', 'married', 'cohabitant', 'widower', 'divorced')
MIN_FORCED_PARTS = 1.0
MAX_FORCED_PARTS = 6.5
HALF = 0.5


def tax_parts(marital, children, disabled_children=0, extra_half_part=False, forced=None, *, max_children):
    """Nombre de parts pour l'IRPP.

    - marié, ou veuf avec enfants : 2 + 0,5 par enfant ;
    - célibataire, divorcé, veuf sans enfant : 1 ; avec n enfants : 2 + 0,5 × (n − 1) ;
    - ``max_children`` enfants au plus (paramètre, 6 en 2026) ;
    - enfant infirme : 1 part au lieu de 0,5 (+0,5 chacun, dans la limite des enfants comptés) ;
    - ``extra_half_part`` : 1,5 part pour une personne seule **sans enfant à charge** ayant
      élevé des enfants, perdu un enfant de 16 ans ou plus, ou invalide ≥ 40 % ;
    - ``forced`` : parts forcées (de 1 à 6,5 par demi-part), prioritaires.
    """
    if forced is not None:
        if not MIN_FORCED_PARTS <= forced <= MAX_FORCED_PARTS or (forced / HALF) % 1:
            raise ValueError(f'Nombre de parts forcé invalide : {forced} (1 à 6,5 par demi-part)')
        return float(forced)
    if marital not in MARITAL_CODES:
        raise ValueError(f'Situation familiale inconnue : {marital!r}')
    if children < 0 or disabled_children < 0:
        raise ValueError(f"Nombre d'enfants négatif : {children}, infirmes {disabled_children}")

    counted = min(children, max_children)
    disabled = min(disabled_children, counted)
    if marital == 'married' or (marital == 'widower' and counted):
        parts = 2 + HALF * counted
    elif counted:
        parts = 2 + HALF * (counted - 1)
    else:
        parts = 1 + (HALF if extra_half_part else 0)
    return parts + HALF * disabled
