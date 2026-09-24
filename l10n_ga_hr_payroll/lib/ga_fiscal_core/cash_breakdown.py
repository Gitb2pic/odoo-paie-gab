"""Billetage des paies en espèces (F2) : nombre de coupures par valeur."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Breakdown:
    counts: tuple  # ((coupure, nombre), ...) par valeur décroissante
    remainder: int  # reste inférieur à la plus petite coupure


def cash_breakdown(amount, denominations):
    """Répartit ``amount`` (FCFA) en coupures, de la plus grande à la plus petite."""
    if amount < 0:
        raise ValueError(f'Montant de billetage négatif : {amount}')
    if not denominations or any(d <= 0 for d in denominations):
        raise ValueError(f'Coupures invalides : {denominations!r}')
    rest = int(amount)
    counts = []
    for denomination in sorted(denominations, reverse=True):
        number, rest = divmod(rest, denomination)
        counts.append((denomination, number))
    return Breakdown(counts=tuple(counts), remainder=rest)
