"""Exonérations par ligne, plafonds par groupe (ADR-17).

Chaque ligne de gain porte un groupe social et un groupe fiscal :

- ``None`` : ligne soumise (cotisations) ou imposable (TCS, IRPP) ;
- un code de ``SOCIAL_CAPS`` / ``TAX_CAPS`` : la part exonérée du groupe est
  calculée sur le total de ses lignes, puis répartie au prorata des lignes
  (arrondi au franc, écart porté sur la dernière ligne : le total est conservé).

Groupes sociaux (arrêtés 016 et 037/MTEPS) : ``EXCLUDED`` (art. 3, exclu en totalité),
``TRANSPORT_35K`` (transport + véhicule + carburant + kilométrique, cumul plafonné),
``ISR_RETIREMENT`` (ISR retraite / décès, cotisable à 50 %).

Groupes fiscaux (CGI art. 91, 91 bis, instruction 144/2004, NC 000134/2004) :
``EXEMPT`` (frais justifiés, exonérés en totalité), ``VEHICLE_100K`` (sans véhicule de
fonction), ``TRANSPORT_DAILY`` (jours de présence × forfait 2 ou 4 trajets),
``FAMILY_20K`` (par enfant et par mois), ``BONUS_4M`` (gratifications, cumul annuel),
``ISR_RETIREMENT`` (imposable à 50 %).

**Indemnité de logement en espèces : aucun groupe** — imposable en totalité tant que le
point 09-5 de la base (seuils 250 000 / 40 %) n'est pas tranché (décision D-14).
Un groupe inconnu lève ``ValueError`` : aucune rubrique ne peut être exonérée par erreur.
"""

from dataclasses import dataclass
from types import MappingProxyType

from .rounding import round_fcfa

TRIPS_2 = 2
TRIPS_4 = 4


@dataclass(frozen=True)
class GainLine:
    code: str
    amount: float
    social_group: str | None = None
    tax_group: str | None = None
    forced_taxable: bool = False  # ex. transport réintégré si l'employeur transporte ou loge


@dataclass(frozen=True)
class ExemptionContext:
    presence_days: float = 0
    transport_trips: int | None = None
    children: int = 0
    ytd_bonus_exempted: float = 0
    has_company_car: bool = False


@dataclass(frozen=True)
class LineExemption:
    code: str
    amount: int
    social_excluded: int
    tax_exempt: int


@dataclass(frozen=True)
class ExemptionResult:
    lines: tuple
    social_excluded: int
    tax_exempt: int
    bonus_exempted: int


def _total(total, _ctx, _p):
    return total


def _social_transport(total, _ctx, p):
    return min(total, p.social_transport_cap)


def _isr_retirement(total, _ctx, p):
    # la part imposable (déclarée) est arrondie au franc ; l'exonération en est le complément
    return total - round_fcfa(total * p.isr_taxable_ratio_retirement)


def _vehicle(total, ctx, p):
    return 0 if ctx.has_company_car else min(total, p.vehicle_monthly_cap)


def _transport_daily(total, ctx, p):
    if ctx.transport_trips is None:
        return 0
    rates = {TRIPS_2: p.transport_daily_2_trips, TRIPS_4: p.transport_daily_4_trips}
    if ctx.transport_trips not in rates:
        raise ValueError(f'Nombre de trajets de transport invalide : {ctx.transport_trips} (2 ou 4)')
    return min(total, ctx.presence_days * rates[ctx.transport_trips])


def _family(total, ctx, p):
    return min(total, ctx.children * p.family_monthly_per_child)


def _bonus(total, ctx, p):
    return min(total, max(0, p.bonus_annual_cap - ctx.ytd_bonus_exempted))


SOCIAL_CAPS = MappingProxyType(
    {
        'EXCLUDED': _total,
        'TRANSPORT_35K': _social_transport,
        'ISR_RETIREMENT': _isr_retirement,
    }
)

TAX_CAPS = MappingProxyType(
    {
        'EXEMPT': _total,
        'VEHICLE_100K': _vehicle,
        'TRANSPORT_DAILY': _transport_daily,
        'FAMILY_20K': _family,
        'BONUS_4M': _bonus,
        'ISR_RETIREMENT': _isr_retirement,
    }
)


def _allocate(lines, registry, group_of, kind, *, ctx, p):
    """Part exonérée de chaque ligne (par index) et total par groupe."""
    groups = {}
    for index, line in enumerate(lines):
        group = group_of(line)
        if group is None:
            continue
        if group not in registry:
            raise ValueError(f'Groupe {kind} inconnu {group!r} sur la rubrique {line.code}')
        if line.amount < 0:
            raise ValueError(f'Montant négatif {line.amount} sur la rubrique {line.code} du groupe {group}')
        groups.setdefault(group, []).append(index)

    shares = [0] * len(lines)
    per_group = {}
    for group, indexes in groups.items():
        total = sum(lines[i].amount for i in indexes)
        exempt = min(round_fcfa(total), max(0, round_fcfa(registry[group](total, ctx, p))))
        per_group[group] = exempt
        allocated = 0
        for position, i in enumerate(indexes):
            if position == len(indexes) - 1:
                shares[i] = exempt - allocated
            else:
                shares[i] = round_fcfa(exempt * lines[i].amount / total) if total else 0
                allocated += shares[i]
    return shares, per_group


def exemptions(lines, ctx, p):
    """Parts exclues de l'assiette sociale et exonérées d'impôt, ligne par ligne."""
    lines = tuple(lines)
    social, _ = _allocate(lines, SOCIAL_CAPS, lambda line: line.social_group, 'social', ctx=ctx, p=p)
    tax, tax_groups = _allocate(
        lines,
        TAX_CAPS,
        lambda line: None if line.forced_taxable else line.tax_group,
        'fiscal',
        ctx=ctx,
        p=p,
    )
    result_lines = tuple(
        LineExemption(code=line.code, amount=round_fcfa(line.amount), social_excluded=s, tax_exempt=t)
        for line, s, t in zip(lines, social, tax, strict=True)
    )
    return ExemptionResult(
        lines=result_lines,
        social_excluded=sum(social),
        tax_exempt=sum(tax),
        bonus_exempted=tax_groups.get('BONUS_4M', 0),
    )
