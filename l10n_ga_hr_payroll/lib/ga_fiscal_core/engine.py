"""Moteur du bulletin gabonais : ``PayslipFacts`` → ``compute`` → ``PayResult``.

Functional Core (patron 1) : fonction pure, sans ``odoo`` ; l'adaptateur du bulletin
(étape 2.3) traduit ``hr.payslip`` en ``PayslipFacts`` et lit ``PayResult``.
Algorithme : base de connaissance, fichier 04 §7. Arrondi au franc à chaque montant de
ligne (règle d'or 9) ; les intermédiaires annuels (RNI, quotient) ne sont pas arrondis.
"""

from dataclasses import dataclass

from .benefits import benefit_amount, benefits_base
from .exemptions import ExemptionContext, GainLine, exemptions
from .parts import tax_parts
from .rounding import round_fcfa
from .social import social_base, social_contributions
from .tax import irpp_monthly, irpp_regularisation, tcs_amount, tcs_base


@dataclass(frozen=True)
class PayslipFacts:
    lines: tuple = ()  # GainLine du mois (espèces)
    benefits: tuple = ()  # avantages en nature à valoriser : 'housing', 'domestic', 'utilities', 'food'
    main_salary: float = 0  # rémunération principale (base de l'avantage nourriture)
    marital: str = 'single'
    children: int = 0
    disabled_children: int = 0
    extra_half_part: bool = False
    forced_parts: float | None = None
    presence_ratio: float = 1.0
    presence_days: float = 0
    transport_trips: int | None = None
    has_company_car: bool = False
    ytd_bonus_exempted: float = 0  # gratifications déjà exonérées dans l'année
    ytd_irpp_base: float = 0  # cumul des bases IRPP mensuelles des bulletins précédents de l'année
    ytd_irpp_withheld: float = 0  # cumul de l'IRPP retenu (régularisations comprises)
    regularize: bool = False  # dernier bulletin de l'année ou départ


@dataclass(frozen=True)
class PayResult:
    lines: tuple  # LineExemption par ligne (parts exclue sociale et exonérée fiscale)
    gains: int
    benefits_in_kind: int
    social_excluded: int
    tax_exempt: int
    bonus_exempted: int
    social_base: int
    taxable_gross: int
    cnss_employee: int
    cnamgs_employee: int
    tcs_base: int
    tcs: int
    tax_parts: float
    irpp_base_monthly: int
    abatement: float
    annual_net_taxable: float
    quotient: float
    irpp: int
    irpp_regularisation: int
    fnh_employee: int
    total_employee_deductions: int
    net: int
    cnss_employer_pf: int
    cnss_employer_at: int
    cnss_employer_avid: int
    cnamgs_employer: int
    fnh: int  # part patronale
    cfp: int
    employer_charges: int
    employer_cost: int

    @property
    def cnss_employer(self):
        return self.cnss_employer_pf + self.cnss_employer_at + self.cnss_employer_avid


def _benefit_lines(facts, ctx, p):
    """Avantages en nature valorisés sur les gains en espèces soumis (D-11)."""
    if not facts.benefits:
        return ()
    cash = exemptions(facts.lines, ctx, p)
    cash_subject = sum(line.amount for line in cash.lines) - cash.social_excluded
    base = benefits_base(cash_subject, p)
    return tuple(
        GainLine(f'AN_{kind.upper()}', benefit_amount(kind, base, facts.main_salary, p)) for kind in facts.benefits
    )


def compute(facts, p):
    """Calcule le bulletin du mois à partir des faits et des paramètres datés."""
    ctx = ExemptionContext(
        presence_days=facts.presence_days,
        transport_trips=facts.transport_trips,
        children=facts.children,
        ytd_bonus_exempted=facts.ytd_bonus_exempted,
        has_company_car=facts.has_company_car,
    )
    benefit_lines = _benefit_lines(facts, ctx, p)
    exo = exemptions(tuple(facts.lines) + benefit_lines, ctx, p)
    gains = sum(line.amount for line in exo.lines)
    benefits_in_kind = sum(line.amount for line in benefit_lines)

    # Cotisations sociales
    base_social = social_base(gains - exo.social_excluded, facts.presence_ratio, p)
    contributions = social_contributions(base_social, p)

    # TCS puis IRPP
    taxable_gross = gains - exo.tax_exempt
    base_tcs = tcs_base(taxable_gross, contributions.cnss_employee, contributions.cnamgs_employee, p)
    tcs = tcs_amount(base_tcs, p)
    parts = tax_parts(
        facts.marital,
        facts.children,
        facts.disabled_children,
        facts.extra_half_part,
        facts.forced_parts,
        p=p,
    )
    irpp_base = base_tcs - tcs
    irpp = irpp_monthly(irpp_base, parts, p)
    regularisation = (
        irpp_regularisation(
            ytd_base=facts.ytd_irpp_base,
            month_base=irpp_base,
            ytd_withheld=facts.ytd_irpp_withheld,
            month_irpp=irpp.monthly,
            parts=parts,
            p=p,
        )
        if facts.regularize
        else 0
    )

    # Charges fiscales patronales
    fnh_total = round_fcfa(min(base_social, p.fnh_ceiling) * p.fnh_rate)
    fnh_employee = round_fcfa(fnh_total * p.fnh_employee_share)
    fnh_employer = fnh_total - fnh_employee
    cfp_base = base_social if p.cfp_base == 'social' else gains
    cfp = round_fcfa(min(cfp_base, p.cfp_ceiling) * p.cfp_rate)

    deductions = (
        contributions.cnss_employee + contributions.cnamgs_employee + tcs + irpp.monthly + regularisation + fnh_employee
    )
    employer_charges = contributions.cnss_employer + contributions.cnamgs_employer + fnh_employer + cfp
    return PayResult(
        lines=exo.lines,
        gains=gains,
        benefits_in_kind=benefits_in_kind,
        social_excluded=exo.social_excluded,
        tax_exempt=exo.tax_exempt,
        bonus_exempted=exo.bonus_exempted,
        social_base=base_social,
        taxable_gross=taxable_gross,
        cnss_employee=contributions.cnss_employee,
        cnamgs_employee=contributions.cnamgs_employee,
        tcs_base=base_tcs,
        tcs=tcs,
        tax_parts=parts,
        irpp_base_monthly=irpp_base,
        abatement=irpp.abatement,
        annual_net_taxable=irpp.annual_net_taxable,
        quotient=irpp.quotient,
        irpp=irpp.monthly,
        irpp_regularisation=regularisation,
        fnh_employee=fnh_employee,
        total_employee_deductions=deductions,
        net=gains - benefits_in_kind - deductions,  # les avantages en nature ne sont pas versés
        cnss_employer_pf=contributions.cnss_employer_pf,
        cnss_employer_at=contributions.cnss_employer_at,
        cnss_employer_avid=contributions.cnss_employer_avid,
        cnamgs_employer=contributions.cnamgs_employer,
        fnh=fnh_employer,
        cfp=cfp,
        employer_charges=employer_charges,
        employer_cost=gains + employer_charges,
    )
