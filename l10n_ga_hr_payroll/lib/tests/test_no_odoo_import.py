"""Règle d'or 2 : le noyau ``ga_fiscal_core`` n'importe jamais ``odoo`` (analyse AST)."""

import ast
from pathlib import Path

import ga_fiscal_core

PACKAGE = Path(ga_fiscal_core.__file__).parent


def _imported_modules(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            yield node.module or ''


def test_package_has_modules():
    assert len(list(PACKAGE.glob('*.py'))) >= 10


def test_no_odoo_import_anywhere():
    offenders = []
    for path in sorted(PACKAGE.rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        offenders += [
            f'{path.name}: {name}' for name in _imported_modules(tree) if name == 'odoo' or name.startswith('odoo.')
        ]
    assert not offenders, offenders


def test_only_standard_library_imports():
    allowed = {'dataclasses', 'datetime', 'decimal', 'math', 'types', 'yaml'}
    for path in sorted(PACKAGE.rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        modules = {name.split('.')[0] for name in _imported_modules(tree)}
        assert modules <= allowed, (path.name, modules - allowed)
