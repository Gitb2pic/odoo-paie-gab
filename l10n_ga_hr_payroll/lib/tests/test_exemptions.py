import pytest
from ga_fiscal_core.exemptions import SOCIAL_CAPS, TAX_CAPS, ExemptionContext, GainLine, exemptions

CTX = ExemptionContext(presence_days=22, transport_trips=2, children=3)


def _by_code(result):
    return {line.code: line for line in result.lines}


def test_registries_are_read_only():
    with pytest.raises(TypeError):
        SOCIAL_CAPS['NEW'] = lambda total, ctx, p: total
    with pytest.raises(TypeError):
        TAX_CAPS['NEW'] = lambda total, ctx, p: total


def test_subject_lines_have_no_exemption(params_2026):
    result = exemptions((GainLine('BASIC', 450_000),), CTX, params_2026)
    assert (result.social_excluded, result.tax_exempt) == (0, 0)


def test_f16_lines(params_2026):
    lines = (
        GainLine('BASIC', 450_000),
        GainLine('TRANSP', 35_000, 'TRANSPORT_35K', 'TRANSPORT_DAILY'),
        GainLine('RESP', 105_000, None, 'EXEMPT'),
    )
    result = exemptions(lines, CTX, params_2026)
    assert (result.social_excluded, result.tax_exempt) == (35_000, 140_000)


def test_shared_social_transport_cap_prorata(params_2026):
    lines = (
        GainLine('TRANSP', 20_000, 'TRANSPORT_35K'),
        GainLine('VEHIC', 30_000, 'TRANSPORT_35K'),
    )
    lines_out = _by_code(exemptions(lines, CTX, params_2026))
    assert lines_out['TRANSP'].social_excluded == 14_000
    assert lines_out['VEHIC'].social_excluded == 21_000


def test_prorata_rounding_keeps_group_total(params_2026):
    lines = (
        GainLine('A', 10_001, 'TRANSPORT_35K'),
        GainLine('B', 10_001, 'TRANSPORT_35K'),
        GainLine('C', 20_001, 'TRANSPORT_35K'),
    )
    result = exemptions(lines, CTX, params_2026)
    assert [line.social_excluded for line in result.lines] == [8_750, 8_750, 17_500]
    assert result.social_excluded == 35_000


def test_excluded_and_exempt_groups_are_total(params_2026):
    result = exemptions((GainLine('DEPL', 80_000, 'EXCLUDED', 'EXEMPT'),), CTX, params_2026)
    assert (result.social_excluded, result.tax_exempt) == (80_000, 80_000)


def test_forced_taxable_keeps_social_treatment(params_2026):
    line = GainLine('TRANSP', 30_000, 'TRANSPORT_35K', 'TRANSPORT_DAILY', forced_taxable=True)
    result = exemptions((line,), CTX, params_2026)
    assert (result.social_excluded, result.tax_exempt) == (30_000, 0)


def test_transport_daily_cap(params_2026):
    line = GainLine('TRANSP', 70_000, None, 'TRANSPORT_DAILY')
    assert exemptions((line,), CTX, params_2026).tax_exempt == 55_000  # 22 j × 2 500
    four_trips = ExemptionContext(presence_days=22, transport_trips=4)
    assert exemptions((line,), four_trips, params_2026).tax_exempt == 70_000  # plafond 110 000
    assert exemptions((line,), ExemptionContext(presence_days=22), params_2026).tax_exempt == 0


def test_transport_daily_rejects_unknown_trips(params_2026):
    line = GainLine('TRANSP', 70_000, None, 'TRANSPORT_DAILY')
    with pytest.raises(ValueError, match='trajets'):
        exemptions((line,), ExemptionContext(presence_days=22, transport_trips=3), params_2026)


def test_vehicle_cap_and_company_car(params_2026):
    line = GainLine('VEHIC', 150_000, None, 'VEHICLE_100K')
    assert exemptions((line,), CTX, params_2026).tax_exempt == 100_000
    with_car = ExemptionContext(has_company_car=True)
    assert exemptions((line,), with_car, params_2026).tax_exempt == 0


def test_family_cap_per_child(params_2026):
    line = GainLine('FAMIL', 75_000, None, 'FAMILY_20K')
    assert exemptions((line,), CTX, params_2026).tax_exempt == 60_000  # 3 enfants


@pytest.mark.parametrize(
    ('ytd', 'expected'),
    [(0, 4_000_000), (3_500_000, 500_000), (4_500_000, 0)],
)
def test_bonus_annual_cap(params_2026, ytd, expected):
    ctx = ExemptionContext(ytd_bonus_exempted=ytd)
    result = exemptions((GainLine('13M', 5_000_000, None, 'BONUS_4M'),), ctx, params_2026)
    assert result.tax_exempt == expected
    assert result.bonus_exempted == expected


def test_isr_retirement_half_taxable(params_2026):
    line = GainLine('ISR_RET', 1_000_001, 'ISR_RETIREMENT', 'ISR_RETIREMENT')
    result = exemptions((line,), CTX, params_2026)
    assert (result.social_excluded, result.tax_exempt) == (500_000, 500_000)


def test_unknown_group_is_explicit_error(params_2026):
    with pytest.raises(ValueError, match='LOGT_ESP'):
        exemptions((GainLine('LOGT', 300_000, None, 'LOGT_ESP'),), CTX, params_2026)
    with pytest.raises(ValueError, match='social'):
        exemptions((GainLine('X', 1, 'NOPE'),), CTX, params_2026)


def test_negative_amount_in_group_rejected(params_2026):
    with pytest.raises(ValueError, match='négatif'):
        exemptions((GainLine('TRANSP', -1_000, 'TRANSPORT_35K'),), CTX, params_2026)


def test_negative_subject_line_allowed(params_2026):
    # une ligne sans groupe peut être négative (rappel négatif, retenue d'absence)
    result = exemptions((GainLine('BASIC', 450_000), GainLine('ABS', -15_000)), CTX, params_2026)
    assert result.social_excluded == 0
