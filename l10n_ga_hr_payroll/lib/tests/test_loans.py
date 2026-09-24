"""Prêts salariés (F1) : échéancier, spécifications d'octroi (patron 12, RG20), quotité saisissable."""

import pytest
import yaml
from ga_fiscal_core.loans import (
    LoanFacts,
    MaxInstallmentRatio,
    MaxOutstanding,
    MinSeniority,
    eligibility_failures,
    schedule,
    seizable_portion,
)
from ga_fiscal_core.param_codes import dated_values, spec_by_code

# Barème art. 729 CPC (base 05 §7) : (de, a, taux) ; a = None sans limite.
SEIZABLE = [
    (0, 25000, 0.05),
    (25000, 50000, 0.10),
    (50000, 75000, 0.20),
    (75000, 100000, 0.25),
    (100000, 150000, 0.30),
    (150000, None, 1.0),
]


@pytest.mark.parametrize(
    ('amount', 'count', 'expected'),
    [
        (600000, 6, [100000] * 6),
        (100000, 3, [33333, 33333, 33334]),
        (1000, 1, [1000]),
        (10, 3, [3, 3, 4]),
    ],
)
def test_schedule(amount, count, expected):
    assert schedule(amount, count) == expected
    assert sum(schedule(amount, count)) == amount


@pytest.mark.parametrize(('amount', 'count'), [(0, 3), (-5, 3), (1000, 0)])
def test_schedule_invalid(amount, count):
    with pytest.raises(ValueError):
        schedule(amount, count)


def _facts(**values):
    base = {
        'seniority_years': 3,
        'installment': 100000,
        'reference_net': 400000,
        'outstanding': 0,
        'amount': 600000,
    }
    base.update(values)
    return LoanFacts(**base)


def _specs(years=2, ratio=0.40, cap=1000000):
    return MinSeniority(years) & MaxInstallmentRatio(ratio) & MaxOutstanding(cap)


def test_all_specs_satisfied():
    assert eligibility_failures(_specs(), _facts()) == []


def test_min_seniority_failure():
    failures = eligibility_failures(_specs(), _facts(seniority_years=1))
    assert [f.code for f in failures] == ['seniority']
    assert failures[0].limit == 2
    assert failures[0].actual == 1


def test_installment_ratio_failure():
    failures = eligibility_failures(_specs(), _facts(installment=160001))
    assert [f.code for f in failures] == ['installment']
    assert failures[0].limit == 160000


def test_installment_ratio_at_limit_ok():
    assert eligibility_failures(_specs(), _facts(installment=160000)) == []


def test_installment_ratio_without_reference_net():
    failures = eligibility_failures(_specs(), _facts(reference_net=0))
    assert [f.code for f in failures] == ['installment']


def test_outstanding_failure():
    failures = eligibility_failures(_specs(), _facts(outstanding=500000))
    assert [f.code for f in failures] == ['outstanding']
    assert failures[0].actual == 1100000


def test_outstanding_no_cap():
    assert eligibility_failures(_specs(cap=0), _facts(outstanding=10**9)) == []


def test_combined_failures_in_order():
    failures = eligibility_failures(_specs(), _facts(seniority_years=0, installment=10**6, outstanding=10**7))
    assert [f.code for f in failures] == ['seniority', 'installment', 'outstanding']


def test_single_spec_leaves():
    assert MinSeniority(2).leaves() == (MinSeniority(2),)
    assert len(_specs().leaves()) == 3


@pytest.mark.parametrize(
    ('net', 'expected'),
    [
        (0, 0),
        (20000, 1000),
        (25000, 1250),
        (50000, 3750),
        (100000, 15000),
        (150000, 30000),
        (160000, 40000),  # exemple de la base 05 §7
        (-5, 0),
    ],
)
def test_seizable_portion(net, expected):
    assert seizable_portion(net, SEIZABLE) == expected


def test_seizable_portion_bounded_brackets():
    assert seizable_portion(10**6, [(0, 100, 0.5)]) == 50


def test_spec_ok_and_first_failure():
    specs = _specs()
    assert specs.ok(_facts())
    assert not specs.ok(_facts(outstanding=10**7))
    assert specs.failure(_facts(seniority_years=0, outstanding=10**7)).code == 'seniority'
    assert MinSeniority(2).ok(_facts())


def test_seizable_brackets_from_yaml(yaml_path):
    data = yaml.safe_load(yaml_path.read_text(encoding='utf-8'))
    [(_day, brackets)] = dated_values(data, spec_by_code('l10n_ga_seizable_brackets'))
    assert brackets == SEIZABLE
    assert seizable_portion(160000, brackets) == 40000
