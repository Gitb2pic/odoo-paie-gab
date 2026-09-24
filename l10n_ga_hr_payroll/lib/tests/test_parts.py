import dataclasses

import pytest
from ga_fiscal_core.parts import tax_parts


@pytest.mark.parametrize(
    ('marital', 'children', 'expected'),
    [
        # tableau 04 §1.3 de la base
        ('single', 0, 1),
        ('divorced', 0, 1),
        ('widower', 0, 1),
        ('married', 0, 2),
        ('single', 1, 2),
        ('divorced', 1, 2),
        ('married', 1, 2.5),
        ('widower', 1, 2.5),  # veuf avec enfants = marié
        ('single', 2, 2.5),
        ('married', 2, 3),
        ('single', 3, 3),
        ('married', 3, 3.5),
        ('single', 4, 3.5),
        # 6 enfants au plus : plafonds 5 (marié) et 4,5 (célibataire)
        ('married', 6, 5),
        ('married', 8, 5),
        ('single', 6, 4.5),
        ('single', 9, 4.5),
        # concubinage : pas marié fiscalement
        ('cohabitant', 0, 1),
        ('cohabitant', 2, 2.5),
    ],
)
def test_parts_table(params_2026, marital, children, expected):
    assert tax_parts(marital, children, p=params_2026) == expected


def test_parts_match_reference_calculator(params_2026, oracle):
    mapping = {'single': 'celibataire', 'married': 'marie', 'widower': 'veuf', 'divorced': 'divorce'}
    for marital, ref in mapping.items():
        for children in range(9):
            for disabled in range(3):
                assert tax_parts(marital, children, disabled, p=params_2026) == oracle.nombre_parts(
                    ref, children, disabled
                ), (marital, children, disabled)


def test_disabled_child_counts_one_part(params_2026):
    assert tax_parts('married', 2, disabled_children=1, p=params_2026) == 3.5
    # infirmes limités aux enfants comptés
    assert tax_parts('married', 1, disabled_children=3, p=params_2026) == 3


def test_extra_half_part_only_without_children(params_2026):
    assert tax_parts('single', 0, extra_half_part=True, p=params_2026) == 1.5
    assert tax_parts('widower', 0, extra_half_part=True, p=params_2026) == 1.5
    # la demi-part spéciale ne concerne que les personnes sans enfant à charge
    assert tax_parts('single', 2, extra_half_part=True, p=params_2026) == 2.5
    assert tax_parts('married', 0, extra_half_part=True, p=params_2026) == 2


@pytest.mark.parametrize('forced', [1, 1.5, 4, 6.5])
def test_forced_parts(params_2026, forced):
    assert tax_parts('single', 0, forced=forced, p=params_2026) == forced


@pytest.mark.parametrize('forced', [0.5, 7, 2.25])
def test_forced_parts_out_of_range(params_2026, forced):
    with pytest.raises(ValueError, match='parts'):
        tax_parts('single', 0, forced=forced, p=params_2026)


@pytest.mark.parametrize(('marital', 'children', 'disabled'), [('unknown', 0, 0), ('single', -1, 0), ('single', 1, -1)])
def test_invalid_input(params_2026, marital, children, disabled):
    with pytest.raises(ValueError):
        tax_parts(marital, children, disabled, p=params_2026)


def test_parts_come_from_parameters(params_2026):
    richer = dataclasses.replace(params_2026, parts_married=2.5, parts_married_per_child=1)
    assert tax_parts('married', 2, p=richer) == 4.5
    assert tax_parts('married', 8, p=dataclasses.replace(params_2026, max_children=4)) == 4
