"""Noyau fiscal pur de la paie gabonaise (ADR-03, règle d'or 2 : aucun import ``odoo``)."""

from .cash_breakdown import Breakdown, cash_breakdown
from .engine import PayResult, PayslipFacts, compute
from .exemptions import SOCIAL_CAPS, TAX_CAPS, ExemptionContext, GainLine, exemptions
from .params import FiscalParams, load_from_yaml
from .parts import tax_parts
from .rounding import CashRounding, cash_round, round_fcfa

__all__ = [
    'SOCIAL_CAPS',
    'TAX_CAPS',
    'Breakdown',
    'CashRounding',
    'ExemptionContext',
    'FiscalParams',
    'GainLine',
    'PayResult',
    'PayslipFacts',
    'cash_breakdown',
    'cash_round',
    'compute',
    'exemptions',
    'load_from_yaml',
    'round_fcfa',
    'tax_parts',
]
