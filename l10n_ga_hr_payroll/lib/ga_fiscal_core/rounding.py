"""Arrondis : au franc (règle d'or 9) et arrondi des paies en espèces (F2, RG23).

Aucun import ``odoo`` : ``round_fcfa`` reproduit ``float_round(x, precision_digits=0)``
(demi vers le haut, loin de zéro) en neutralisant le bruit des flottants.
"""

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# Chiffres significatifs conservés avant l'arrondi au franc : absorbe le bruit
# binaire (13057.500000000002, 2.4999999999999996) sans toucher aux montants réels.
_NOISE_DIGITS = 6
# Valeurs des règles d'arrondi espèces (F2, D-44), après le NET unique : reliquat du bulletin
# précédent, ajustement d'arrondi (≤ 0), montant versé.
CASH_PREV = 'cash_prev'
CASH_ADJUST = 'cash_adjust'
CASH_PAY = 'cash_pay'
CASH_VALUES = frozenset({CASH_PREV, CASH_ADJUST, CASH_PAY})


def round_fcfa(value):
    """Arrondit un montant au franc, demi vers le haut (loin de zéro)."""
    cleaned = Decimal(str(round(float(value), _NOISE_DIGITS)))
    return int(cleaned.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class CashRounding:
    paid: int
    carry: int


def cash_round(net, carry_in, step, final=False):
    """Montant versé en espèces et reliquat reporté au bulletin suivant.

    ``paid`` = multiple inférieur de ``step`` de ``net + carry_in`` ; le reste est
    reporté (``carry``). ``step == 0`` désactive l'arrondi. Au solde de tout compte
    (``final``), tout est versé. Un total négatif n'est pas versé : il est reporté.
    """
    if step < 0:
        raise ValueError(f"Pas d'arrondi espèces négatif : {step}")
    total = round_fcfa(net) + round_fcfa(carry_in)
    if final or step == 0:
        return CashRounding(paid=total, carry=0)
    if total < 0:
        return CashRounding(paid=0, carry=total)
    paid = math.floor(total / step) * step
    return CashRounding(paid=paid, carry=total - paid)
