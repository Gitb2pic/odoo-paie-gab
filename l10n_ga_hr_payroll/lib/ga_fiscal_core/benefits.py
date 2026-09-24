"""Avantages en nature, évaluation forfaitaire (CGI art. 93 ; base, fichier 04 §5).

Logement 6 %, domesticité 5 %, eau et électricité 5 % du salaire brut diminué des
cotisations sociales ; nourriture 25 % de la rémunération principale, plafonnée.
Le véhicule n'est pas prévu par l'art. 93 (point à vérifier) : aucun forfait.

Base (décision D-11) : l'avantage entre lui-même dans l'assiette, la définition
« brut − cotisations » est donc circulaire ; on retient les gains en espèces soumis
moins les cotisations salariales calculées sur ces seuls gains, sans itération.
"""

from .rounding import round_fcfa
from .social import social_contributions


def benefits_base(cash_subject_gains, p):
    """Base des avantages logement, domesticité, eau/électricité (D-11)."""
    contributions = social_contributions(cash_subject_gains, p)
    return round_fcfa(cash_subject_gains) - contributions.cnss_employee - contributions.cnamgs_employee


def benefit_amount(kind, base, main_salary, p):
    """Valeur mensuelle d'un avantage en nature, arrondie au franc."""
    if kind not in p.benefit_rates:
        raise ValueError(f'Avantage en nature inconnu : {kind!r} (attendu : {sorted(p.benefit_rates)})')
    rate = p.benefit_rates[kind]
    if kind == 'food':
        return round_fcfa(min(main_salary * rate, p.food_monthly_cap))
    return round_fcfa(base * rate)
