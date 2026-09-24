import pytest
from ga_fiscal_core.cash_breakdown import cash_breakdown

DENOMINATIONS = (10_000, 5_000, 2_000, 1_000, 500)


def test_breakdown_greedy():
    result = cash_breakdown(514_500, DENOMINATIONS)
    assert result.counts == ((10_000, 51), (5_000, 0), (2_000, 2), (1_000, 0), (500, 1))
    assert result.remainder == 0
    assert sum(d * n for d, n in result.counts) == 514_500


def test_breakdown_remainder_below_smallest_denomination():
    result = cash_breakdown(17_897, DENOMINATIONS)
    assert result.counts == ((10_000, 1), (5_000, 1), (2_000, 1), (1_000, 0), (500, 1))
    assert result.remainder == 397


def test_breakdown_sorts_denominations():
    assert cash_breakdown(1_500, (500, 1_000)).counts == ((1_000, 1), (500, 1))


def test_breakdown_zero():
    result = cash_breakdown(0, DENOMINATIONS)
    assert all(n == 0 for _d, n in result.counts)
    assert result.remainder == 0


@pytest.mark.parametrize(('amount', 'denominations'), [(-1, DENOMINATIONS), (1_000, ()), (1_000, (500, 0))])
def test_breakdown_rejects_invalid_input(amount, denominations):
    with pytest.raises(ValueError):
        cash_breakdown(amount, denominations)
