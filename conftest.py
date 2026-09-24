"""Collecte pytest des tests purs situés dans un addon Odoo (ex. ``l10n_ga_hr_payroll/lib/tests``).

Un addon est un paquet Python dont ``__init__.py`` importe ``odoo`` : collecté comme
``pytest.Package``, il serait importé et ferait échouer les tests sans Odoo. Tout dossier
situé dans un addon est donc collecté comme simple répertoire (les tests purs n'ont pas
d'``__init__.py`` et importent ``ga_fiscal_core`` via ``pythonpath``).
"""

from pathlib import Path

import pytest


def _in_addon(path: Path) -> bool:
    return any((folder / '__manifest__.py').exists() for folder in (path, *path.parents))


def pytest_collect_directory(path, parent):
    if _in_addon(path):
        return pytest.Dir.from_parent(parent, path=path)
    return None
