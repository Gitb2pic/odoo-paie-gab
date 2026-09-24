import pytest
from ga_fiscal_core.rounding import cash_round, round_fcfa


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (13057.5, 13058),
        (13057.499, 13057),
        (0.5, 1),
        (1.5, 2),
        (2.5, 3),  # demi vers le haut (float_round d'Odoo), pas l'arrondi bancaire
        (-2.5, -3),
        (0, 0),
        (261150 * 0.05, 13058),  # bruit flottant 13057.500000000002
        (2.4999999999999996, 3),  # bruit flottant sous le demi
    ],
)
def test_round_fcfa_half_up(value, expected):
    assert round_fcfa(value) == expected
    assert isinstance(round_fcfa(value), int)


def test_cash_round_floor_to_step_with_carry():
    result = cash_round(514_897, 0, 500)
    assert (result.paid, result.carry) == (514_500, 397)
    result = cash_round(514_897, 397, 500)
    assert (result.paid, result.carry) == (515_000, 294)


def test_cash_round_twelve_months_keeps_every_franc():
    nets = [514_897, 486_617, 459_002, 740_547, 520_123, 499_999, 500_001, 1_234, 613_377, 488_888, 505_050, 777_777]
    carry = 0
    paid = []
    for net in nets:
        result = cash_round(net, carry, 500)
        assert result.paid % 500 == 0
        assert 0 <= result.carry < 500
        paid.append(result.paid)
        carry = result.carry
    assert sum(paid) + carry == sum(nets)


def test_cash_round_final_payslip_pays_everything():
    result = cash_round(514_897, 397, 500, final=True)
    assert (result.paid, result.carry) == (515_294, 0)


def test_cash_round_step_zero_disables_rounding():
    result = cash_round(514_897, 0, 0)
    assert (result.paid, result.carry) == (514_897, 0)


def test_cash_round_negative_total_is_carried_not_paid():
    result = cash_round(-700, 0, 500)
    assert (result.paid, result.carry) == (0, -700)
    result = cash_round(1_000, -700, 500)
    assert (result.paid, result.carry) == (0, 300)


def test_cash_round_rejects_negative_step():
    with pytest.raises(ValueError, match='arrondi'):
        cash_round(1_000, 0, -500)
