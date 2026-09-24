#!/usr/bin/env python3
"""Contrôles du dépôt non couverts par ruff / pylint-odoo (CLAUDE.md §3 et §7-C3).

- syntaxe antérieure à Odoo 19 : ``_sql_constraints``, ``attrs=``, ``<tree`` ;
- noyau ``lib/ga_fiscal_core`` : aucun import ``odoo`` (règle d'or 2).

Usage : check_odoo19_rules.py FICHIER... (appelé par pre-commit).
"""

import ast
import re
import sys
from pathlib import Path

PRE19_PATTERNS = {
    '.py': [(re.compile(r'\b_sql_constraints\b'), '_sql_constraints : utiliser models.Constraint')],
    '.xml': [
        (re.compile(r'\battrs\s*='), 'attrs= : utiliser invisible="..." / readonly="..." directs'),
        (re.compile(r'<tree\b'), '<tree> : utiliser <list>'),
    ],
}
CORE_MARKER = 'lib/ga_fiscal_core/'


def _odoo_imports(source, filename):
    tree = ast.parse(source, filename=filename)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or '']
        else:
            continue
        for name in names:
            if name == 'odoo' or name.startswith('odoo.'):
                yield node.lineno, name


def check_file(path):
    """Retourne la liste des violations « chemin:ligne: message » du fichier."""
    errors = []
    text = path.read_text(encoding='utf-8')
    for pattern, message in PRE19_PATTERNS.get(path.suffix, []):
        for lineno, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                errors.append(f'{path}:{lineno}: {message}')
    if path.suffix == '.py' and CORE_MARKER in path.as_posix():
        errors.extend(
            f'{path}:{lineno}: import {name} interdit dans ga_fiscal_core'
            for lineno, name in _odoo_imports(text, str(path))
        )
    return errors


def main(argv):
    errors = []
    for arg in argv:
        path = Path(arg)
        if path.suffix in PRE19_PATTERNS and path.is_file():
            errors.extend(check_file(path))
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
