#!/usr/bin/env python3
"""Contrôle C3 (FIX 02) : chaque champ ``l10n_ga_*`` cité dans une vue existe sur le modèle ciblé.

Incident du 25/09/2026 : une vue citait un champ que le processus Odoo ne connaissait pas encore.
Ce contrôle statique, lancé par ``make lint``, attrape la variante « code » de cette erreur : champ
mal orthographié, défini sur un autre modèle, ou fichier Python absent. Il ne remplace pas le
redémarrage du service après une modification Python (règle CLAUDE.md §5).

Méthode : les champs sont lus dans les classes Python du dépôt (``_name`` / ``_inherit``,
affectations ``nom = fields.Xxx(...)``) ; les vues ``ir.ui.view`` (modèle de la vue) sont lues
dans les XML. Seuls les champs préfixés ``l10n_ga_`` sont vérifiés (les champs d'Odoo ne sont
pas dans le dépôt). Les champs d'une sous-vue (liste d'un One2many) visent un autre modèle :
ils doivent seulement exister sur un modèle du dépôt.

Usage : check_view_fields.py [RACINE_DU_DEPOT]
"""

import ast
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

PREFIX = 'l10n_ga_'
MODULE_GLOB = 'l10n_ga_*'


def _model_names(node):
    """Modèles d'une classe Odoo : ``_name`` sinon ``_inherit`` (chaîne ou liste)."""
    values = {}
    for statement in node.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = statement.targets[0]
            if isinstance(target, ast.Name) and target.id in ('_name', '_inherit'):
                values[target.id] = statement.value
    value = values.get('_name') or values.get('_inherit')
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return [value.value]
    if isinstance(value, ast.List | ast.Tuple):
        return [v.value for v in value.elts if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    return []


def _is_field(value, factories=frozenset()):
    """``fields.Xxx(...)`` ou appel d'une fonction du module qui renvoie un champ (ex. ``_frozen_amount``)."""
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return func.value.id == 'fields'
    return isinstance(func, ast.Name) and func.id in factories


def _field_factories(tree):
    """Fonctions de module qui renvoient ``fields.Xxx(...)``."""
    return frozenset(
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and any(isinstance(sub, ast.Return) and _is_field(sub.value) for sub in ast.walk(node))
    )


def python_fields(root):
    """``{modèle: {champs}}`` définis dans les modules du dépôt."""
    fields = defaultdict(set)
    for path in root.glob(f'{MODULE_GLOB}/**/*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        factories = _field_factories(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            names = {
                target.id
                for statement in node.body
                if isinstance(statement, ast.Assign) and _is_field(statement.value, factories)
                for target in statement.targets
                if isinstance(target, ast.Name)
            }
            for model in _model_names(node):
                fields[model] |= names
    return fields


SUB_VIEW = re.compile(r"field\[@name=['\"][^'\"]+['\"]\]/(list|form|kanban)")


def _top_level_fields(arch):
    """``(élément, sous-vue)`` des champs de la vue ; ``sous-vue`` vrai quand le champ est dans la liste
    ou le formulaire d'un autre champ (modèle lié, inconnu hors d'Odoo)."""

    def walk(element, sub_view):
        for child in element:
            if child.tag == 'field':
                yield child, sub_view
                yield from walk(child, True)
            elif child.tag == 'xpath':
                yield from walk(child, sub_view or bool(SUB_VIEW.search(child.get('expr', ''))))
            else:
                yield from walk(child, sub_view)

    yield from walk(arch, False)


def _line(lines, name):
    """Ligne du premier ``name="…"`` du fichier (ElementTree ne garde pas les numéros de ligne)."""
    marker = f'name="{name}"'
    return next((index for index, text in enumerate(lines, start=1) if marker in text), 0)


def view_fields(path):
    """``[(modèle ou None pour une sous-vue, champ, ligne)]`` des champs ``l10n_ga_*`` des vues du fichier."""
    tree = ET.parse(path)
    lines = path.read_text(encoding='utf-8').splitlines()
    found = []
    for record in tree.iter('record'):
        if record.get('model') != 'ir.ui.view':
            continue
        model = record.find("field[@name='model']")
        arch = record.find("field[@name='arch']")
        if model is None or arch is None or not (model.text or '').strip():
            continue
        for element, sub_view in _top_level_fields(arch):
            name = element.get('name', '')
            if name.startswith(PREFIX):
                found.append((None if sub_view else model.text.strip(), name, _line(lines, name)))
    return found


def check(root):
    root = Path(root)
    known = python_fields(root)
    anywhere = set().union(*known.values()) if known else set()
    errors = []
    for path in sorted(root.glob(f'{MODULE_GLOB}/**/*.xml')):
        for model, name, line in view_fields(path):
            if model is None:  # sous-vue : le champ doit au moins exister sur un modèle du dépôt
                if name not in anywhere:
                    errors.append(f'{path}:{line}: champ « {name} » défini sur aucun modèle du dépôt')
            elif name not in known.get(model, set()):
                errors.append(f'{path}:{line}: champ « {name} » absent du modèle « {model} » en Python')
    return errors


def main(argv):
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[1]
    errors = check(root)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
