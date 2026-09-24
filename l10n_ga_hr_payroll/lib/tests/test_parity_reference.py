"""Parité avec le calculateur validé ``calcul_paie_gabon_reference.py`` (oracle, CLAUDE.md §2).

Écart toléré : 1 FCFA par montant (l'oracle arrondit avec ``round`` bancaire, le noyau
au demi supérieur comme ``float_round`` d'Odoo ; la CNSS patronale est arrondie par
branche PF / AT / AVID).
"""

import itertools

import pytest
from ga_fiscal_core.engine import PayslipFacts, compute
from ga_fiscal_core.exemptions import GainLine

GAINS = (200_000, 350_000, 545_000, 850_000, 1_500_000, 2_000_000, 3_200_000, 5_000_000)
FAMILIES = (
    ('single', 'celibataire', 0),
    ('single', 'celibataire', 1),
    ('married', 'marie', 2),
    ('married', 'marie', 3),
    ('widower', 'veuf', 2),
    ('divorced', 'divorce', 4),
)
EXEMPTIONS = ((0, 0), (30_000, 30_000), (35_000, 140_000), (0, 50_000))

COMPARED = {
    'cnss_sal': 'cnss_employee',
    'cnamgs_sal': 'cnamgs_employee',
    'base_tcs': 'tcs_base',
    'tcs': 'tcs',
    'irpp': 'irpp',
    'net_a_payer': 'net',
    'cnss_pat': 'cnss_employer',
    'cnamgs_pat': 'cnamgs_employer',
    'fnh': 'fnh',
    'cfp': 'cfp',
    'cout_employeur': 'employer_cost',
    'assiette_sociale': 'social_base',
    'brut_imposable': 'taxable_gross',
    'parts': 'tax_parts',
}


def _lines(gains, social_excluded, tax_exempt):
    """Lignes produisant exactement les exclusions sociale et fiscale demandées."""
    both = min(social_excluded, tax_exempt)
    lines = [GainLine('BASIC', gains - social_excluded - tax_exempt + both)]
    if both:
        lines.append(GainLine('DEPL', both, 'EXCLUDED', 'EXEMPT'))
    if social_excluded - both:
        lines.append(GainLine('PANIER', social_excluded - both, 'EXCLUDED', None))
    if tax_exempt - both:
        lines.append(GainLine('RESP', tax_exempt - both, None, 'EXEMPT'))
    return tuple(lines)


CASES = list(itertools.product(GAINS, FAMILIES, EXEMPTIONS))


@pytest.mark.parametrize(
    ('gains', 'family', 'exempt'), CASES, ids=[f'{g}-{f[0]}{f[2]}-{e[0]}-{e[1]}' for g, f, e in CASES]
)
def test_engine_matches_reference(params_2026, oracle, gains, family, exempt):
    marital, reference_marital, children = family
    social_excluded, tax_exempt = exempt
    facts = PayslipFacts(lines=_lines(gains, social_excluded, tax_exempt), marital=marital, children=children)
    result = compute(facts, params_2026)
    expected = oracle.Bulletin(gains, social_excluded, tax_exempt, reference_marital, children).calcul()
    gaps = {
        ref_key: (expected[ref_key], getattr(result, key))
        for ref_key, key in COMPARED.items()
        if abs(expected[ref_key] - getattr(result, key)) > 1
    }
    assert not gaps, gaps


def test_grid_size():
    assert len(CASES) >= 60
