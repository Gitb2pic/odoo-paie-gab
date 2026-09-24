"""Table champ FiscalParams ↔ code ``hr.rule.parameter`` ↔ chemin YAML (étape 2.2)."""

import dataclasses
import math
from datetime import date

import pytest
from ga_fiscal_core.param_codes import COMPANY_OPTIONS, PARAMETERS, dated_values, params_from_values, spec_by_code
from ga_fiscal_core.params import FiscalParams, load_from_yaml

CHECK_DATES = ('2025-12-31', '2026-01-01', '2026-07-16', '2026-07-17')


def _yaml(yaml_path):
    import yaml  # noqa: PLC0415

    with open(yaml_path, encoding='utf-8') as stream:
        return yaml.safe_load(stream)


def _values_at(data, on_date):
    """Valeur de chaque code à ``on_date`` (dernière date d'effet <= date, RG06)."""
    values = {}
    for spec in PARAMETERS:
        applicable = [(d, v) for d, v in dated_values(data, spec) if d <= on_date]
        values[spec.code] = max(applicable)[1]
    return values


def test_codes_are_prefixed_and_unique():
    codes = [spec.code for spec in PARAMETERS]
    assert len(codes) == len(set(codes))
    assert all(code.startswith('l10n_ga_') for code in codes)


def test_every_fiscal_field_has_a_code():
    fields = {f.name for f in dataclasses.fields(FiscalParams)}
    covered = {spec.field for spec in PARAMETERS if spec.field and not spec.field.startswith('benefit_rate_')}
    covered |= {'benefit_rates', *COMPANY_OPTIONS}
    assert fields == covered


def test_min_withholding_code_is_the_f14_name():
    assert spec_by_code('l10n_ga_irpp_min_withholding').field == 'irpp_min_withholding'


def test_spec_by_code_unknown():
    with pytest.raises(KeyError):
        spec_by_code('l10n_ga_nope')


@pytest.mark.parametrize('on_date', CHECK_DATES)
def test_params_from_values_matches_yaml_loader(yaml_path, on_date):
    day = date.fromisoformat(on_date)
    values = _values_at(_yaml(yaml_path), day)
    built = params_from_values(values, cash_rounding=500)
    assert built == load_from_yaml(yaml_path, day)


def test_dated_values_keeps_every_effective_date(yaml_path):
    data = _yaml(yaml_path)
    dates = [d.isoformat() for d, _ in dated_values(data, spec_by_code('l10n_ga_cnss_employee_rate'))]
    assert dates == ['2000-01-01', '2026-01-01']
    fnh = dated_values(data, spec_by_code('l10n_ga_fnh_rate'))
    assert [v for _, v in fnh] == [0.02, 0.03]


def test_undated_scalar_uses_sentinel_date(yaml_path):
    (only,) = dated_values(_yaml(yaml_path), spec_by_code('l10n_ga_hours_month_ref'))
    assert only[0].isoformat() == '2000-01-01'
    assert only[1] == 173.33


def test_brackets_are_python_literals_with_open_upper_bound(yaml_path):
    ((_, brackets),) = dated_values(_yaml(yaml_path), spec_by_code('l10n_ga_irpp_brackets'))
    assert brackets[-1][1] is None
    assert all(isinstance(row, tuple) and len(row) == 4 for row in brackets)
    params = params_from_values(_values_at(_yaml(yaml_path), date(2026, 1, 1)), cash_rounding=0)
    assert params.irpp_brackets[-1][1] == math.inf


def test_missing_code_is_explicit(yaml_path):
    values = _values_at(_yaml(yaml_path), date(2026, 1, 1))
    del values['l10n_ga_tcs_rate']
    with pytest.raises(ValueError, match='l10n_ga_tcs_rate'):
        params_from_values(values, cash_rounding=500)


def test_company_options_are_passed_through(yaml_path):
    values = _values_at(_yaml(yaml_path), date(2026, 1, 1))
    params = params_from_values(values, cash_rounding=1000, cfp_base='gross')
    assert (params.cash_rounding, params.cfp_base) == (1000, 'gross')


def test_missing_yaml_key_is_explicit():
    with pytest.raises(ValueError, match='cnss'):
        dated_values({}, spec_by_code('l10n_ga_cnss_ceiling'))
