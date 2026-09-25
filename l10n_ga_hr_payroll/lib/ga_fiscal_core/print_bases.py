"""Base et taux imprimés par rubrique du bulletin (F7, plan 2.7 b, E3).

Fonction pure : lit le ``PayResult`` et les ``FiscalParams`` du bulletin ; aucune valeur en dur.
Les taux sont en pourcentage ; ``None`` = sans objet (barème IRPP, régularisation).
"""

PERCENT = 100


def print_bases(result, p):
    """Valeur du noyau (``l10n_ga_core_value``) → (base, taux %) ; seules les cotisations et impôts."""
    cnss_base = min(result.social_base, p.cnss_ceiling)
    cnamgs_base = min(result.social_base, p.cnamgs_ceiling)
    fnh_base = min(result.social_base, p.fnh_ceiling)
    cfp_gross = result.social_base if p.cfp_base == 'social' else result.gains
    cfp_base = min(cfp_gross, p.cfp_ceiling)
    fnh_employee_rate = p.fnh_rate * p.fnh_employee_share
    return {
        'cnss_employee': (cnss_base, p.cnss_employee_rate * PERCENT),
        'cnss_employer_pf': (cnss_base, p.cnss_employer_pf_rate * PERCENT),
        'cnss_employer_at': (cnss_base, p.cnss_employer_at_rate * PERCENT),
        'cnss_employer_avid': (cnss_base, p.cnss_employer_avid_rate * PERCENT),
        'cnamgs_employee': (cnamgs_base, p.cnamgs_employee_rate * PERCENT),
        'cnamgs_employer': (cnamgs_base, p.cnamgs_employer_rate * PERCENT),
        'fnh_employee': (fnh_base, fnh_employee_rate * PERCENT),
        'fnh': (fnh_base, (p.fnh_rate - fnh_employee_rate) * PERCENT),
        'cfp': (cfp_base, p.cfp_rate * PERCENT),
        'tcs': (result.tcs_base, p.tcs_rate * PERCENT),
        'irpp': (result.irpp_base_monthly, None),
        'irpp_regularisation': (None, None),
    }
