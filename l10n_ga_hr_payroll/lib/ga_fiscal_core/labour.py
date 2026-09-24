"""Droit du travail : ancienneté, heures supplémentaires, allocation de congé (base, fichier 05 §2 à §5).

Fonctions pures, sans ``odoo`` : les taux et les tranches viennent de la convention collective
(ancienneté, heures supplémentaires — aucune valeur par défaut, point 09-11) et les constantes
des congés des paramètres datés (décision D-23). Arrondi au franc sur le montant de la ligne.
"""

import math

from .rounding import round_fcfa


def completed_years(start, on):
    """Années révolues entre la date d'ancienneté ``start`` et ``on`` (0 si absente ou future)."""
    if not start or on < start:
        return 0
    return on.year - start.year - ((on.month, on.day) < (start.month, start.day))


def seniority_rate(years, *, start_years, start_rate, step_rate, max_rate):
    """Taux de la prime d'ancienneté : 0 avant ``start_years``, puis début + pas annuel, plafonné.

    ``max_rate`` = 0 : pas de plafond.
    """
    if min(start_years, start_rate, step_rate, max_rate) < 0:
        raise ValueError('Règle d’ancienneté invalide : valeurs négatives')
    if years < start_years:
        return 0.0
    rate = start_rate + step_rate * (years - start_years)
    return min(rate, max_rate) if max_rate else rate


def overtime_amount(hourly_rate, hours, tranches):
    """Heures supplémentaires d'une période, majorées par tranches.

    ``tranches`` : ``((de, a, majoration), ...)`` en heures du mois, ``a`` = ``None`` sans limite.
    Des heures non couvertes par une tranche lèvent ``ValueError`` : aucun taux n'est supposé.
    """
    if not hours:
        return 0
    amount = 0.0
    covered = 0.0
    for start, end, rate in tranches:
        upper = math.inf if end is None else end
        portion = max(0.0, min(hours, upper) - start)
        covered += portion
        amount += hourly_rate * portion * (1 + rate)
    if covered < hours:
        raise ValueError(f'{hours - covered:g} heure(s) supplémentaire(s) sans taux de majoration dans la convention')
    return round_fcfa(amount)


def leave_allowance(*, maintained, reference_pay, ratio, days_taken, annual_days):
    """Allocation de congé (circulaire n°565) : le plus favorable du maintien et de la fraction.

    Fraction = rémunération de référence × ``ratio`` (1/12, 5/48 pour un mineur) × jours
    ouvrables pris / jours ouvrables du congé annuel.
    """
    if annual_days <= 0:
        raise ValueError('Nombre de jours ouvrables du congé annuel nul')
    if days_taken <= 0:
        return 0
    fraction = reference_pay * ratio * days_taken / annual_days
    return round_fcfa(max(maintained, fraction))
