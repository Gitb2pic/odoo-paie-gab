"""TCS et IRPP (base de connaissance, fichier 04 §1, §2 et §7).

Méthode d'annualisation du mois : chaque mois vaut 1/12 de l'année ; la
régularisation annuelle recalcule l'impôt sur le cumul réel (dernier bulletin de
l'année ou départ).
"""

from dataclasses import dataclass

from .rounding import round_fcfa

MONTHS = 12


def tcs_base(taxable_gross, cnss_employee, cnamgs_employee, p):
    """Base TCS = brut imposable − cotisations salariales déductibles (options 09-3)."""
    base = taxable_gross
    if p.tcs_deduct_cnss:
        base -= cnss_employee
    if p.tcs_deduct_cnamgs:
        base -= cnamgs_employee
    return round_fcfa(base)


def tcs_amount(base, p):
    """TCS = taux × (base − fraction exonérée mensuelle), jamais négative."""
    return round_fcfa(max(0, base - p.tcs_monthly_exemption) * p.tcs_rate)


def tax_one_part(quotient, brackets):
    """Impôt annuel pour une part : taux × Q − constante de la tranche de Q."""
    if quotient < 0:
        raise ValueError(f'quotient familial négatif : {quotient}')
    for _low, high, rate, constant in brackets:
        if quotient <= high:
            return max(0.0, rate * quotient - constant)
    raise ValueError(f'quotient {quotient} hors barème')  # pragma: no cover — dernière borne infinie


@dataclass(frozen=True)
class IrppDetail:
    annual_base: float
    abatement: float
    annual_net_taxable: float
    quotient: float
    annual_tax: float
    monthly: int


def _annual_tax(annual_base, parts, p):
    if parts <= 0:
        raise ValueError(f'nombre de parts invalide : {parts}')
    annual_base = max(0, annual_base)
    abatement = min(annual_base * p.fp_rate, p.fp_annual_cap)
    net_taxable = annual_base - abatement
    quotient = net_taxable / parts
    return abatement, net_taxable, quotient, tax_one_part(quotient, p.irpp_brackets) * parts


def irpp_monthly(monthly_base, parts, p):
    """IRPP du mois par annualisation ; seuil minimal de retenue F14 (0 = désactivé)."""
    annual_base = monthly_base * MONTHS
    abatement, net_taxable, quotient, annual_tax = _annual_tax(annual_base, parts, p)
    monthly = round_fcfa(annual_tax / MONTHS)
    if 0 < monthly <= p.irpp_min_withholding:
        monthly = 0
    return IrppDetail(
        annual_base=max(0, annual_base),
        abatement=abatement,
        annual_net_taxable=net_taxable,
        quotient=quotient,
        annual_tax=annual_tax,
        monthly=monthly,
    )


def irpp_regularisation(*, ytd_base, month_base, ytd_withheld, month_irpp, parts, p):
    """Écart entre l'IRPP dû sur le cumul réel de l'année et l'IRPP déjà retenu.

    ``ytd_*`` : cumuls des bulletins précédents de l'année (cumuls d'ouverture compris) ;
    ``month_*`` : bulletin en cours. Positif = retenue complémentaire, négatif = restitution.
    """
    *_detail, annual_tax = _annual_tax(ytd_base + month_base, parts, p)
    return round_fcfa(annual_tax) - round_fcfa(ytd_withheld) - round_fcfa(month_irpp)
