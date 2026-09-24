"""Prêts salariés (F1) : échéancier, conditions d'octroi (patron 12 Specification, RG20), quotité saisissable.

Fonctions pures, sans ``odoo`` : les seuils (ancienneté, part du net, plafond d'encours) et le
barème de la quotité saisissable (art. 729 CPC, base 05 §7) sont passés par l'appelant depuis
les paramètres datés et la société (décisions D-32, D-37). Les messages traduits sont produits
par le modèle Odoo à partir du code de l'échec.
"""

import math
from dataclasses import dataclass

from .rounding import round_fcfa


def schedule(amount, count):
    """Mensualités égales au franc ; la dernière absorbe l'écart d'arrondi."""
    if amount <= 0 or count <= 0:
        raise ValueError('Montant et nombre d’échéances doivent être strictement positifs')
    installment = amount // count
    return [installment] * (count - 1) + [amount - installment * (count - 1)]


@dataclass(frozen=True)
class LoanFacts:
    seniority_years: int  # années révolues à la date d'octroi
    installment: float  # mensualité demandée
    reference_net: float  # net du dernier bulletin validé (D-31), 0 si aucun
    outstanding: float  # encours des autres prêts du salarié
    amount: float  # montant du prêt demandé


@dataclass(frozen=True)
class Failure:
    code: str  # 'seniority' | 'installment' | 'outstanding'
    limit: float
    actual: float


class Spec:
    """Condition d'octroi combinable par ``&`` (patron 12).

    Chaque sous-classe définit ``failure(facts)`` : ``None`` si la condition est remplie, sinon un ``Failure``.
    """

    def ok(self, facts):
        return self.failure(facts) is None

    def leaves(self):
        return (self,)

    def __and__(self, other):
        return AndSpec(self.leaves() + other.leaves())


@dataclass(frozen=True)
class AndSpec(Spec):
    specs: tuple

    def failure(self, facts):
        return next((f for f in (s.failure(facts) for s in self.specs) if f), None)

    def leaves(self):
        return self.specs


@dataclass(frozen=True)
class MinSeniority(Spec):
    years: int

    def failure(self, facts):
        if facts.seniority_years >= self.years:
            return None
        return Failure('seniority', self.years, facts.seniority_years)


@dataclass(frozen=True)
class MaxInstallmentRatio(Spec):
    ratio: float

    def failure(self, facts):
        limit = round_fcfa(facts.reference_net * self.ratio)
        if facts.reference_net > 0 and facts.installment <= limit:
            return None
        return Failure('installment', limit, facts.installment)


@dataclass(frozen=True)
class MaxOutstanding(Spec):
    ceiling: float  # 0 = pas de plafond

    def failure(self, facts):
        total = facts.outstanding + facts.amount
        if not self.ceiling or total <= self.ceiling:
            return None
        return Failure('outstanding', self.ceiling, total)


def eligibility_failures(spec, facts):
    """Toutes les conditions non satisfaites, dans l'ordre de la combinaison."""
    return [failure for failure in (leaf.failure(facts) for leaf in spec.leaves()) if failure]


def seizable_portion(net, brackets):
    """Quotité saisissable progressive par tranches ``(de, a, taux)`` (``a`` = ``None`` : sans limite)."""
    if net <= 0:
        return 0
    total = 0.0
    for start, end, rate in brackets:
        upper = math.inf if end is None else end
        total += max(0.0, min(net, upper) - start) * rate
    return round_fcfa(total)
