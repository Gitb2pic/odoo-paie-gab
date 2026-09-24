"""Paramètres fiscaux et sociaux datés (Parameter Object, patron 3).

Côté Odoo, ``FiscalParams`` est construit depuis ``hr.rule.parameter`` à la date de
fin du bulletin (RG06, D-06). ``load_from_yaml`` ne sert qu'aux tests purs : il lit
``parametres_fiscaux_gabon_2026.yaml`` avec la même règle de date. Aucun taux,
plafond ni barème n'est écrit dans le code (règle d'or 1).
"""

import math
from dataclasses import dataclass, field
from datetime import date as date_cls
from types import MappingProxyType

CFP_BASES = ('social', 'gross')
BENEFIT_KINDS = ('housing', 'domestic', 'utilities', 'food')


@dataclass(frozen=True)
class FiscalParams:
    # SMIG et CNSS
    smig: float
    cnss_ceiling: float
    cnss_employee_rate: float
    cnss_employer_pf_rate: float
    cnss_employer_at_rate: float
    cnss_employer_avid_rate: float
    social_transport_cap: float
    # CNAMGS
    cnamgs_ceiling: float
    cnamgs_employee_rate: float
    cnamgs_employer_rate: float
    # TCS
    tcs_rate: float
    tcs_monthly_exemption: float
    tcs_deduct_cnss: bool
    tcs_deduct_cnamgs: bool
    # IRPP
    fp_rate: float
    fp_annual_cap: float
    max_children: int
    irpp_brackets: tuple  # ((de, a, taux, constante), ...) pour 1 part, dernière borne = inf
    irpp_min_withholding: float
    # Exonérations (art. 91, 91 bis, instruction 144/2004, NC 000134/2004)
    bonus_annual_cap: float
    vehicle_monthly_cap: float
    transport_daily_2_trips: float
    transport_daily_4_trips: float
    family_monthly_per_child: float
    isr_taxable_ratio_retirement: float
    # Avantages en nature (art. 93)
    benefit_rates: MappingProxyType
    food_monthly_cap: float
    # FNH, CFP
    fnh_rate: float
    fnh_ceiling: float
    fnh_employee_share: float
    cfp_rate: float
    cfp_ceiling: float
    cfp_base: str = 'social'  # D-10
    # Paie en espèces (F2) : l'arrondi est une option société
    cash_rounding: float = 500
    cash_denominations: tuple = field(default=())

    def __post_init__(self):
        if self.cfp_base not in CFP_BASES:
            raise ValueError(f'cfp_base doit valoir {CFP_BASES}, reçu {self.cfp_base!r}')
        if not self.irpp_brackets:
            raise ValueError('barème IRPP vide')
        if set(self.benefit_rates) != set(BENEFIT_KINDS):
            raise ValueError(f'taux d’avantages en nature incomplets : {sorted(self.benefit_rates)}')


def _as_date(value):
    return value if isinstance(value, date_cls) else date_cls.fromisoformat(str(value))


def _dated(node, on_date, name):
    """Valeur applicable à ``on_date`` : dernière ``date_from`` <= date (RG06).

    Un scalaire est une valeur non datée, valable à toute date.
    """
    if not isinstance(node, list):
        return node
    applicable = [e for e in node if _as_date(e['date_from']) <= on_date]
    if not applicable:
        raise ValueError(f'Aucune valeur de {name} au {on_date.isoformat()}')
    return max(applicable, key=lambda e: _as_date(e['date_from']))['valeur']


def _brackets(rows):
    return tuple((row['de'], math.inf if row['a'] is None else row['a'], row['taux'], row['constante']) for row in rows)


def load_from_yaml(path, on_date, **options):
    """Charge les paramètres applicables à ``on_date`` depuis le YAML de la base.

    ``options`` remplace des champs non fiscaux ou des options société
    (``cash_rounding``, ``cfp_base``, ``tcs_deduct_cnamgs``…).
    """
    import yaml  # noqa: PLC0415 — outil de test, jamais chargé par Odoo

    with open(path, encoding='utf-8') as stream:
        data = yaml.safe_load(stream)
    on_date = _as_date(on_date)

    def get(section, key):
        return _dated(data[section][key], on_date, f'{section}.{key}')

    irpp = data['irpp']
    exo = irpp['exonerations']
    benefits = irpp['avantages_en_nature']
    values = {
        'smig': _dated(data['smig'], on_date, 'smig'),
        'cnss_ceiling': get('cnss', 'plafond_mensuel'),
        'cnss_employee_rate': get('cnss', 'taux_salarial'),
        'cnss_employer_pf_rate': get('cnss', 'taux_patronal_prestations_familiales'),
        'cnss_employer_at_rate': get('cnss', 'taux_patronal_accidents_travail'),
        'cnss_employer_avid_rate': get('cnss', 'taux_patronal_pensions_avid'),
        'social_transport_cap': get('cnss', 'exoneration_frais_transport_vehicule_carburant_km_mensuelle'),
        'cnamgs_ceiling': get('cnamgs', 'plafond_mensuel'),
        'cnamgs_employee_rate': get('cnamgs', 'taux_salarial'),
        'cnamgs_employer_rate': get('cnamgs', 'taux_patronal'),
        'tcs_rate': get('tcs', 'taux'),
        'tcs_monthly_exemption': get('tcs', 'fraction_exoneree_mensuelle'),
        'tcs_deduct_cnss': get('tcs', 'deduire_cnss_salariale'),
        'tcs_deduct_cnamgs': get('tcs', 'deduire_cnamgs_salariale'),
        'fp_rate': get('irpp', 'abattement_frais_professionnels_taux'),
        'fp_annual_cap': get('irpp', 'abattement_frais_professionnels_plafond_annuel'),
        'max_children': get('irpp', 'nombre_max_enfants'),
        'irpp_brackets': _brackets(irpp['bareme_annuel_une_part']),
        'irpp_min_withholding': get('irpp', 'retenue_minimale'),
        'bonus_annual_cap': exo['gratifications_plafond_annuel'],
        'vehicle_monthly_cap': exo['indemnite_vehicule_plafond_mensuel'],
        'transport_daily_2_trips': exo['transport_journalier_2_trajets'],
        'transport_daily_4_trips': exo['transport_journalier_4_trajets'],
        'family_monthly_per_child': exo['primes_familiales_par_enfant_mensuel'],
        'isr_taxable_ratio_retirement': exo['isr_part_imposable_retraite_deces'],
        'benefit_rates': MappingProxyType(
            {
                'housing': benefits['logement'],
                'domestic': benefits['domesticite'],
                'utilities': benefits['eau_electricite'],
                'food': benefits['nourriture'],
            }
        ),
        'food_monthly_cap': benefits['nourriture_plafond_mensuel'],
        'fnh_rate': get('fnh', 'taux'),
        'fnh_ceiling': get('fnh', 'plafond_mensuel'),
        'fnh_employee_share': get('fnh', 'repartition_salarie'),
        'cfp_rate': get('cfp', 'taux'),
        'cfp_ceiling': get('cfp', 'plafond_mensuel_par_salarie'),
        'cash_denominations': tuple(data['paie']['coupures_billetage']),
    }
    values.update(options)
    return FiscalParams(**values)
