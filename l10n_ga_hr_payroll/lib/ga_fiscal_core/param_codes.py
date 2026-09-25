"""Correspondance champ ``FiscalParams`` ↔ code ``hr.rule.parameter`` ↔ chemin du YAML.

Table unique partagée par :

- ``tools/yaml_to_rule_parameters.py`` (build) : YAML → ``data/hr_rule_parameters_data.xml`` ;
- l'adaptateur Odoo ``hr.payslip._l10n_ga_params()`` (étape 2.3) : valeurs lues par code
  à la date du bulletin → ``params_from_values`` → ``FiscalParams``.

Les valeurs sont des littéraux Python (lus par ``safe_eval`` côté Odoo, sprint 0 point 11) :
le barème IRPP est une liste de tuples ``(de, a, taux, constante)`` dont la dernière borne
haute vaut ``None`` (``inf`` n'est pas un littéral). Un scalaire non daté du YAML reçoit la
date d'effet sentinelle ``SENTINEL_DATE``. Les options société (arrondi espèces, base de la
CFP) ne sont pas des paramètres datés : elles sont passées à ``params_from_values``.
"""

import math
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType

from .params import BENEFIT_KINDS, FiscalParams

SENTINEL_DATE = date(2000, 1, 1)
COMPANY_OPTIONS = ('cash_rounding', 'cfp_base')

VALUE = 'value'
BRACKETS = 'brackets'
RATE_BRACKETS = 'rate_brackets'  # tranches (de, a, taux) sans constante : quotité saisissable
LIST = 'list'


@dataclass(frozen=True)
class ParamSpec:
    field: str | None  # champ de FiscalParams ; None = paramètre de paie hors noyau (étapes 2.4+)
    code: str
    path: tuple  # clés successives dans le YAML
    name: str  # libellé du paramètre dans Odoo
    kind: str = VALUE


def _p(field, code, path, name, kind=VALUE):
    return ParamSpec(field, code, tuple(path.split('.')), name, kind)


_BENEFIT_FIELDS = {kind: f'benefit_rate_{kind}' for kind in BENEFIT_KINDS}

PARAMETERS = (
    # SMIG, références de temps (heures supplémentaires, étape 2.4)
    _p('smig', 'l10n_ga_smig_amount', 'smig', 'Gabon : SMIG mensuel'),
    _p(None, 'l10n_ga_rmm_amount', 'rmm', 'Gabon : rémunération minimale mensuelle'),
    _p(None, 'l10n_ga_hours_month_ref', 'heures_mensuelles_reference', 'Gabon : heures mensuelles de référence'),
    _p(None, 'l10n_ga_days_month_ref', 'jours_mensuels_reference', 'Gabon : jours mensuels de référence'),
    # Congés payés (base 05 §5, D-23) : lus par l'adaptateur, hors FiscalParams
    _p(
        None,
        'l10n_ga_leave_ratio_adult',
        'conges.allocation_ratio_adulte',
        'Gabon : allocation de congé, part de la rémunération de référence (adulte)',
    ),
    _p(
        None,
        'l10n_ga_leave_ratio_minor',
        'conges.allocation_ratio_mineur',
        'Gabon : allocation de congé, part de la rémunération de référence (moins de 18 ans)',
    ),
    _p(
        None,
        'l10n_ga_leave_days_month_adult',
        'conges.jours_ouvrables_par_mois_adulte',
        'Gabon : jours ouvrables de congé acquis par mois (adulte)',
    ),
    _p(
        None,
        'l10n_ga_leave_days_month_minor',
        'conges.jours_ouvrables_par_mois_mineur',
        'Gabon : jours ouvrables de congé acquis par mois (moins de 18 ans)',
    ),
    _p(
        None,
        'l10n_ga_leave_working_days_week',
        'conges.jours_ouvrables_par_semaine',
        'Gabon : jours ouvrables par semaine',
    ),
    _p(None, 'l10n_ga_majority_age', 'conges.age_majorite', 'Gabon : âge de la majorité (congés des mineurs)'),
    # CNSS
    _p('cnss_ceiling', 'l10n_ga_cnss_ceiling', 'cnss.plafond_mensuel', 'Gabon : plafond mensuel CNSS'),
    _p('cnss_employee_rate', 'l10n_ga_cnss_employee_rate', 'cnss.taux_salarial', 'Gabon : taux salarial CNSS'),
    _p(
        'cnss_employer_pf_rate',
        'l10n_ga_cnss_pf_rate',
        'cnss.taux_patronal_prestations_familiales',
        'Gabon : taux patronal CNSS prestations familiales',
    ),
    _p(
        'cnss_employer_at_rate',
        'l10n_ga_cnss_at_rate',
        'cnss.taux_patronal_accidents_travail',
        'Gabon : taux patronal CNSS accidents du travail',
    ),
    _p(
        'cnss_employer_avid_rate',
        'l10n_ga_cnss_avid_rate',
        'cnss.taux_patronal_pensions_avid',
        'Gabon : taux patronal CNSS pensions (AVID)',
    ),
    _p(
        'social_transport_cap',
        'l10n_ga_cnss_transport_cap',
        'cnss.exoneration_frais_transport_vehicule_carburant_km_mensuelle',
        'Gabon : exclusion sociale transport, véhicule, carburant (mensuelle)',
    ),
    # CNAMGS
    _p('cnamgs_ceiling', 'l10n_ga_cnamgs_ceiling', 'cnamgs.plafond_mensuel', 'Gabon : plafond mensuel CNAMGS'),
    _p('cnamgs_employee_rate', 'l10n_ga_cnamgs_employee_rate', 'cnamgs.taux_salarial', 'Gabon : taux salarial CNAMGS'),
    _p('cnamgs_employer_rate', 'l10n_ga_cnamgs_employer_rate', 'cnamgs.taux_patronal', 'Gabon : taux patronal CNAMGS'),
    # TCS
    _p('tcs_rate', 'l10n_ga_tcs_rate', 'tcs.taux', 'Gabon : taux de la TCS'),
    _p(
        'tcs_monthly_exemption',
        'l10n_ga_tcs_exemption',
        'tcs.fraction_exoneree_mensuelle',
        'Gabon : fraction mensuelle exonérée de TCS',
    ),
    _p('tcs_deduct_cnss', 'l10n_ga_tcs_deduct_cnss', 'tcs.deduire_cnss_salariale', 'Gabon : TCS après CNSS salariale'),
    _p(
        'tcs_deduct_cnamgs',
        'l10n_ga_tcs_deduct_cnamgs',
        'tcs.deduire_cnamgs_salariale',
        'Gabon : TCS après CNAMGS salariale (point 09-3)',
    ),
    # IRPP
    _p(
        'fp_rate',
        'l10n_ga_irpp_fp_rate',
        'irpp.abattement_frais_professionnels_taux',
        'Gabon : taux de l’abattement pour frais professionnels',
    ),
    _p(
        'fp_annual_cap',
        'l10n_ga_irpp_fp_cap',
        'irpp.abattement_frais_professionnels_plafond_annuel',
        'Gabon : plafond annuel de l’abattement pour frais professionnels',
    ),
    _p('max_children', 'l10n_ga_irpp_max_children', 'irpp.nombre_max_enfants', 'Gabon : nombre maximal d’enfants'),
    _p(
        'irpp_brackets',
        'l10n_ga_irpp_brackets',
        'irpp.bareme_annuel_une_part',
        'Gabon : barème annuel IRPP pour une part',
        BRACKETS,
    ),
    _p(
        'irpp_min_withholding',
        'l10n_ga_irpp_min_withholding',
        'irpp.retenue_minimale',
        'Gabon : retenue IRPP minimale (F14, 0 = désactivé)',
    ),
    # Quotient familial (RG03)
    _p(
        'parts_single',
        'l10n_ga_parts_single',
        'irpp.parts.celibataire_divorce_veuf_sans_enfant',
        'Gabon : parts, personne seule sans enfant',
    ),
    _p(
        'parts_single_extra',
        'l10n_ga_parts_single_extra',
        'irpp.parts.celibataire_ayant_eleve_enfants_ou_invalide',
        'Gabon : parts, personne seule ayant élevé des enfants ou invalide',
    ),
    _p('parts_married', 'l10n_ga_parts_married', 'irpp.parts.marie_sans_enfant', 'Gabon : parts, marié sans enfant'),
    _p(
        'parts_single_first_child',
        'l10n_ga_parts_single_first_child',
        'irpp.parts.celibataire_divorce_premier_enfant',
        'Gabon : parts, personne seule, premier enfant',
    ),
    _p(
        'parts_single_per_extra_child',
        'l10n_ga_parts_single_per_child',
        'irpp.parts.par_enfant_supplementaire',
        'Gabon : parts, personne seule, par enfant supplémentaire',
    ),
    _p(
        'parts_married_per_child',
        'l10n_ga_parts_married_per_child',
        'irpp.parts.marie_ou_veuf_par_enfant',
        'Gabon : parts, marié ou veuf, par enfant',
    ),
    _p(
        'parts_disabled_child',
        'l10n_ga_parts_disabled_child',
        'irpp.parts.enfant_infirme_supplement',
        'Gabon : parts, supplément par enfant infirme',
    ),
    _p('forced_parts_min', 'l10n_ga_parts_forced_min', 'irpp.parts.forcees_minimum', 'Gabon : parts forcées minimum'),
    _p('forced_parts_max', 'l10n_ga_parts_forced_max', 'irpp.parts.forcees_maximum', 'Gabon : parts forcées maximum'),
    # Exonérations (art. 91, 91 bis, instruction 144/2004, NC 000134/2004)
    _p(
        'bonus_annual_cap',
        'l10n_ga_exempt_bonus_cap',
        'irpp.exonerations.gratifications_plafond_annuel',
        'Gabon : plafond annuel d’exonération des gratifications',
    ),
    _p(
        'vehicle_monthly_cap',
        'l10n_ga_exempt_vehicle_cap',
        'irpp.exonerations.indemnite_vehicule_plafond_mensuel',
        'Gabon : plafond mensuel d’exonération de l’indemnité de véhicule',
    ),
    _p(
        'transport_daily_2_trips',
        'l10n_ga_exempt_transport_2_trips',
        'irpp.exonerations.transport_journalier_2_trajets',
        'Gabon : exonération journalière du transport (2 trajets)',
    ),
    _p(
        'transport_daily_4_trips',
        'l10n_ga_exempt_transport_4_trips',
        'irpp.exonerations.transport_journalier_4_trajets',
        'Gabon : exonération journalière du transport (4 trajets)',
    ),
    _p(
        'family_monthly_per_child',
        'l10n_ga_exempt_family_per_child',
        'irpp.exonerations.primes_familiales_par_enfant_mensuel',
        'Gabon : exonération mensuelle des primes familiales par enfant',
    ),
    _p(
        'isr_taxable_ratio_retirement',
        'l10n_ga_isr_retirement_ratio',
        'irpp.exonerations.isr_part_imposable_retraite_deces',
        'Gabon : part imposable de l’ISR retraite ou décès',
    ),
    _p(
        None,
        'l10n_ga_isr_resignation_ratio',
        'irpp.exonerations.isr_part_imposable_demission',
        'Gabon : part imposable de l’ISR démission',
    ),
    # Avantages en nature (art. 93)
    _p(
        _BENEFIT_FIELDS['housing'],
        'l10n_ga_aik_housing_rate',
        'irpp.avantages_en_nature.logement',
        'Gabon : AN logement',
    ),
    _p(
        _BENEFIT_FIELDS['domestic'],
        'l10n_ga_aik_domestic_rate',
        'irpp.avantages_en_nature.domesticite',
        'Gabon : AN domesticité',
    ),
    _p(
        _BENEFIT_FIELDS['utilities'],
        'l10n_ga_aik_utilities_rate',
        'irpp.avantages_en_nature.eau_electricite',
        'Gabon : AN eau et électricité',
    ),
    _p(
        _BENEFIT_FIELDS['food'], 'l10n_ga_aik_food_rate', 'irpp.avantages_en_nature.nourriture', 'Gabon : AN nourriture'
    ),
    _p(
        'food_monthly_cap',
        'l10n_ga_aik_food_cap',
        'irpp.avantages_en_nature.nourriture_plafond_mensuel',
        'Gabon : plafond mensuel de l’AN nourriture',
    ),
    # FNH, CFP
    _p('fnh_rate', 'l10n_ga_fnh_rate', 'fnh.taux', 'Gabon : taux du FNH'),
    _p('fnh_ceiling', 'l10n_ga_fnh_ceiling', 'fnh.plafond_mensuel', 'Gabon : plafond mensuel du FNH'),
    _p(
        'fnh_employee_share',
        'l10n_ga_fnh_employee_share',
        'fnh.repartition_salarie',
        'Gabon : part salariale du FNH (point 09-2)',
    ),
    _p('cfp_rate', 'l10n_ga_cfp_rate', 'cfp.taux', 'Gabon : taux de la CFP'),
    _p('cfp_ceiling', 'l10n_ga_cfp_ceiling', 'cfp.plafond_mensuel_par_salarie', 'Gabon : plafond mensuel de la CFP'),
    # Paie en espèces (F2)
    _p(
        'cash_denominations',
        'l10n_ga_cash_denominations',
        'paie.coupures_billetage',
        'Gabon : coupures du billetage',
        LIST,
    ),
    _p(
        None,
        'l10n_ga_cash_rounding_default',
        'paie.arrondi_especes_defaut',
        'Gabon : arrondi espèces par défaut des sociétés',
    ),
    # Prêts salariés (F1, RG20, D-31, D-32, D-37) : lus par le modèle de prêt, hors FiscalParams
    _p(
        None,
        'l10n_ga_loan_min_seniority_years',
        'prets.anciennete_minimale_annees',
        'Gabon : prêts, ancienneté minimale (années)',
    ),
    _p(
        None,
        'l10n_ga_loan_max_installment_ratio',
        'prets.mensualite_max_ratio_net',
        'Gabon : prêts, mensualité maximale en part du net',
    ),
    _p(
        None,
        'l10n_ga_seizable_brackets',
        'prets.quotite_saisissable',
        'Gabon : quotité saisissable (art. 729 CPC)',
        RATE_BRACKETS,
    ),
    # Déclaration annuelle des salaires (l10n_ga_dgi_edi, étape 4.4) : lus par le générateur DAS
    _p(None, 'l10n_ga_das_id19_threshold', 'das.seuil_id19_mensuel', 'Gabon : DAS, seuil mensuel de l’ID19'),
    _p(None, 'l10n_ga_das_id20_threshold', 'das.seuil_id20_mensuel', 'Gabon : DAS, seuil des tranches de l’ID20'),
    _p(None, 'l10n_ga_das_id21_lines', 'das.lignes_par_feuille_id21', 'Gabon : DAS, lignes par feuille de l’ID21'),
)

_BY_CODE = MappingProxyType({spec.code: spec for spec in PARAMETERS})


def spec_by_code(code):
    return _BY_CODE[code]


def _as_date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _literal(spec, value):
    if spec.kind == BRACKETS:
        return [(row['de'], row['a'], row['taux'], row['constante']) for row in value]
    if spec.kind == RATE_BRACKETS:
        return [(row['de'], row['a'], row['taux']) for row in value]
    if spec.kind == LIST:
        return list(value)
    return value


def _is_dated(node):
    return isinstance(node, list) and bool(node) and all(isinstance(e, dict) and 'date_from' in e for e in node)


def dated_values(data, spec):
    """Liste ``[(date d'effet, littéral), ...]`` triée par date, lue dans le YAML chargé ``data``."""
    node = data
    for key in spec.path:
        if not isinstance(node, dict) or key not in node:
            raise ValueError(f'Clé YAML absente pour {spec.code} : {".".join(spec.path)}')
        node = node[key]
    if _is_dated(node):
        rows = sorted(((_as_date(e['date_from']), e['valeur']) for e in node), key=lambda row: row[0])
        return [(day, _literal(spec, value)) for day, value in rows]
    return [(SENTINEL_DATE, _literal(spec, node))]


def params_from_values(values, **options):
    """``FiscalParams`` depuis ``{code: valeur}`` (valeurs applicables à une date) et les options société."""
    kwargs = {}
    benefits = {}
    for spec in PARAMETERS:
        if spec.field is None:
            continue
        if spec.code not in values:
            raise ValueError(f'Paramètre {spec.code} absent')
        value = values[spec.code]
        if spec.kind == BRACKETS:
            value = tuple((de, math.inf if a is None else a, rate, const) for de, a, rate, const in value)
        elif spec.kind == LIST:
            value = tuple(value)
        if spec.field.startswith('benefit_rate_'):
            benefits[spec.field.removeprefix('benefit_rate_')] = value
        else:
            kwargs[spec.field] = value
    kwargs['benefit_rates'] = MappingProxyType(benefits)
    kwargs.update(options)
    return FiscalParams(**kwargs)
