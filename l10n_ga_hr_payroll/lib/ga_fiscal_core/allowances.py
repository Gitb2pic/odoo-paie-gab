"""Indemnités récurrentes (F15, ADR-16) : montant du mois et prorata des jours de validité.

Fonctions pures, sans ``odoo``. Le montant est celui d'un mois complet de validité ; la
proratisation par la présence reste celle de la règle salariale (``l10n_ga_prorate``, ADR-16 §4).
"""

from .rounding import round_fcfa

FIXED = 'fixed'
WAGE_PERCENT = 'wage_percent'
QUANTITY_RATE = 'quantity_rate'
MODES = (FIXED, WAGE_PERCENT, QUANTITY_RATE)
PERCENT = 100


def allowance_amount(mode, value, quantity, wage):
    """Montant mensuel : fixe, ``value`` % du salaire, ou ``quantity`` × ``value``."""
    if mode == FIXED:
        return round_fcfa(value)
    if mode == WAGE_PERCENT:
        return round_fcfa(wage * value / PERCENT)
    if mode == QUANTITY_RATE:
        return round_fcfa(quantity * value)
    raise ValueError(f'Mode d’indemnité inconnu : {mode!r}')


def validity_ratio(start, end, date_from, date_to):
    """Jours calendaires de validité dans la période / jours calendaires de la période (D-35).

    ``end`` = ``None`` : sans date de fin.
    """
    if date_to < date_from:
        raise ValueError('Période invalide : fin avant le début')
    first = max(start, date_from)
    last = min(end, date_to) if end else date_to
    period_days = (date_to - date_from).days + 1
    return max(0, (last - first).days + 1) / period_days
