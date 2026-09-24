"""Fixtures des tests purs du noyau (sans Odoo)."""

import importlib.util
from datetime import date
from pathlib import Path

import pytest
from ga_fiscal_core.params import load_from_yaml

REPO = Path(__file__).resolve().parents[3]
KB = REPO / 'docs' / 'base_connaissance'
YAML_PATH = KB / 'parametres_fiscaux_gabon_2026.yaml'
ORACLE_PATH = KB / 'calcul_paie_gabon_reference.py'

# Date à laquelle l'oracle (calcul_paie_gabon_reference.py) fixe ses taux :
# CNSS 2026 et FNH 3 %.
ORACLE_DATE = date(2026, 9, 30)


@pytest.fixture(scope='session')
def yaml_path():
    return YAML_PATH


@pytest.fixture(scope='session')
def params_2026():
    return load_from_yaml(YAML_PATH, ORACLE_DATE)


@pytest.fixture(scope='session')
def oracle():
    spec = importlib.util.spec_from_file_location('calcul_paie_gabon_reference', ORACLE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
