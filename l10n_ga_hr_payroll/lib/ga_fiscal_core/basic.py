"""Salaire de base sur le mois de référence (FIX 01, arrêté 016/MTEPS art. 5, base 05 §2).

Taux horaire unique du mois = salaire / heures de référence (paramètre daté ``l10n_ga_hours_month_ref``) ;
la ligne de base paie ``heures de référence − heures non payées``. Les heures réelles du calendrier ne
servent qu'à mesurer les absences, jamais à calculer le taux. Aucun import ``odoo``.
"""

from .rounding import round_fcfa

DEDUCT = 'deduct'  # entrée / sortie : heures hors contrat retirées comme une absence (D-104, défaut)
PRORATA = 'prorata'  # entrée / sortie : heures de référence × heures du contrat / heures prévues
METHODS = (DEDUCT, PRORATA)


def hourly_rate(wage, reference_hours):
    """Taux horaire unique du mois."""
    if not reference_hours:
        raise ValueError('heures mensuelles de référence nulles')
    return wage / reference_hours


def basic_quantity(reference_hours, unpaid_hours, out_hours, planned_hours, method=DEDUCT):
    """Heures payées par la ligne de base, jamais négatives.

    ``unpaid_hours`` : heures du contrat non payées par la base (absences non rémunérées, congé payé
    réglé par l'allocation, CNSS sans subrogation) ; ``out_hours`` : heures hors contrat du mois ;
    ``planned_hours`` : heures prévues du mois (calendrier, hors contrat comprises).
    """
    if method not in METHODS:
        raise ValueError(f'méthode inconnue : {method!r}')
    if method == PRORATA and planned_hours:
        base = reference_hours * (planned_hours - out_hours) / planned_hours
    else:
        base = reference_hours - out_hours
    return max(0.0, base - unpaid_hours)


def basic_amount(wage, reference_hours, quantity):
    """Montant de la ligne de base : le salaire exact si rien n'est retiré, sinon quantité × taux au franc."""
    if quantity >= reference_hours:
        return wage
    return round_fcfa(quantity * hourly_rate(wage, reference_hours))
