"""Import des variables du mois (F3, patron 13 « Pipes and Filters », D-41 à D-43).

Fonctions pures, sans ``odoo`` ni ``openpyxl`` : la lecture du classeur et l'écriture dans
``hr.payslip.input`` / ``hr.work.entry`` restent dans l'assistant Odoo. Chaque filtre prend
des lignes et renvoie ``(lignes valides, anomalies)`` ; une anomalie rejette sa ligne, jamais
le fichier (sauf en-tête fatal). Les anomalies portent un code et une valeur : les messages
traduits sont construits côté Odoo.
"""

import math
from dataclasses import dataclass, field, replace

AMOUNT = 'amount'
HOURS = 'hours'
KEY_LABEL = 'matricule'
NAME_LABELS = ('salarié', 'salarie', 'nom')
CODE_SEPARATORS = ('—', ' - ')
SPACES = (' ', ' ', ' ', '\t')

# Codes d'anomalie
MISSING_KEY_COLUMN = 'missing_key_column'
DUPLICATE_COLUMN = 'duplicate_column'
UNKNOWN_COLUMN = 'unknown_column'
UNKNOWN_EMPLOYEE = 'unknown_employee'
NOT_IN_BATCH = 'not_in_batch'
DUPLICATE_EMPLOYEE = 'duplicate_employee'
INVALID_NUMBER = 'invalid_number'
NEGATIVE_NUMBER = 'negative_number'


@dataclass(frozen=True)
class ImportContext:
    """Référentiels du lot, préparés par l'assistant.

    ``columns`` : code → (``AMOUNT`` | ``HOURS``, id du type d'entrée ou de prestation) ;
    ``employees_by_ref`` : matricule → id ; ``employees_by_name`` : nom → ids ; ``batch`` : ids du lot.
    """

    columns: dict
    employees_by_ref: dict
    employees_by_name: dict
    batch: frozenset


@dataclass(frozen=True)
class Issue:
    row: int | None
    column: str | None
    code: str
    value: object = None
    fatal: bool = False


@dataclass(frozen=True)
class Column:
    index: int
    code: str
    kind: str
    target: int


@dataclass(frozen=True)
class Headers:
    key_index: int
    name_index: int | None
    columns: tuple  # (index, code)


@dataclass(frozen=True)
class Layout:
    key_index: int
    name_index: int | None
    columns: tuple  # Column


@dataclass(frozen=True)
class ImportRow:
    row: int
    cells: tuple
    employee: int | None = None
    values: tuple = field(default=())  # (code, montant ou heures)


def _text(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _header_code(label):
    for separator in CODE_SEPARATORS:
        label = label.split(separator, 1)[0]
    return label.strip()


def normalise_headers(header):
    """Repère la colonne matricule, la colonne nom et le code de chaque autre colonne."""
    key_index = name_index = None
    seen = {}
    for index, raw in enumerate(header):
        label = _text(raw)
        if not label:
            continue
        lowered = label.lower()
        if lowered == KEY_LABEL:
            key_index = index
        elif lowered in NAME_LABELS:
            name_index = index
        else:
            seen.setdefault(_header_code(label), []).append(index)
    if key_index is None:
        return None, (Issue(None, None, MISSING_KEY_COLUMN, fatal=True),)
    issues = tuple(Issue(None, code, DUPLICATE_COLUMN) for code, indexes in seen.items() if len(indexes) > 1)
    columns = tuple((indexes[0], code) for code, indexes in seen.items() if len(indexes) == 1)
    return Headers(key_index, name_index, columns), issues


def resolve_columns(headers, ctx):
    """Associe chaque code d'en-tête à un type d'entrée ou de prestation du lot."""
    columns = []
    issues = []
    for index, code in headers.columns:
        if code in ctx.columns:
            kind, target = ctx.columns[code]
            columns.append(Column(index, code, kind, target))
        else:
            issues.append(Issue(None, code, UNKNOWN_COLUMN))
    return Layout(headers.key_index, headers.name_index, tuple(columns)), tuple(issues)


def _cell(row, index):
    return row.cells[index] if index is not None and index < len(row.cells) else None


def resolve_employee(rows, layout, ctx):
    """Matricule connu ; matricule vide → nom exact s'il est unique (D-41)."""
    kept = []
    issues = []
    for row in rows:
        reference = _text(_cell(row, layout.key_index))
        if reference:
            employee = ctx.employees_by_ref.get(reference)
        else:
            reference = _text(_cell(row, layout.name_index))
            matches = ctx.employees_by_name.get(reference, ())
            employee = matches[0] if len(matches) == 1 else None
        if employee is None:
            issues.append(Issue(row.row, None, UNKNOWN_EMPLOYEE, reference))
        else:
            kept.append(replace(row, employee=employee))
    return tuple(kept), tuple(issues)


def check_in_batch(rows, layout, ctx):
    """Le salarié doit avoir un bulletin brouillon dans le lot."""
    kept = tuple(row for row in rows if row.employee in ctx.batch)
    issues = tuple(Issue(row.row, None, NOT_IN_BATCH, row.employee) for row in rows if row.employee not in ctx.batch)
    return kept, issues


def dedupe(rows, layout, ctx):
    """Un salarié présent sur plusieurs lignes : toutes ses lignes sont refusées."""
    counts = {}
    for row in rows:
        counts[row.employee] = counts.get(row.employee, 0) + 1
    kept = tuple(row for row in rows if counts[row.employee] == 1)
    issues = tuple(Issue(row.row, None, DUPLICATE_EMPLOYEE, row.employee) for row in rows if counts[row.employee] > 1)
    return kept, issues


def parse_number(raw):
    """Nombre d'une cellule : numérique, ou texte « 1 500 » / « 12,5 ». ``ValueError`` sinon."""
    if isinstance(raw, bool):
        raise ValueError(raw)
    if isinstance(raw, int | float):
        number = float(raw)
    elif isinstance(raw, str):
        text = raw
        for space in SPACES:
            text = text.replace(space, '')
        number = float(text.replace(',', '.'))
    else:
        raise ValueError(raw)
    if not math.isfinite(number):
        raise ValueError(raw)
    return number


def parse_amounts(rows, layout, ctx):
    """Montants et heures (décimales acceptées) ; vide = inchangé ; négatif ou texte → ligne refusée."""
    kept = []
    issues = []
    for row in rows:
        values = []
        row_issues = []
        for column in layout.columns:
            raw = _cell(row, column.index)
            if _text(raw) == '':
                continue
            try:
                number = parse_number(raw)
            except ValueError:
                row_issues.append(Issue(row.row, column.code, INVALID_NUMBER, raw))
                continue
            if number < 0:
                row_issues.append(Issue(row.row, column.code, NEGATIVE_NUMBER, raw))
                continue
            values.append((column.code, number))
        if row_issues:
            issues += row_issues
        else:
            kept.append(replace(row, values=tuple(values)))
    return tuple(kept), tuple(issues)


ROW_PIPELINE = (resolve_employee, check_in_batch, dedupe, parse_amounts)


def run(header, raw_rows, ctx):
    """Exécute le pipeline : ``raw_rows`` = [(n° de ligne, cellules)] → (lignes valides, anomalies)."""
    headers, issues = normalise_headers(header)
    if headers is None:
        return (), issues
    layout, column_issues = resolve_columns(headers, ctx)
    issues += column_issues
    rows = tuple(ImportRow(number, tuple(cells)) for number, cells in raw_rows if any(_text(cell) for cell in cells))
    for step in ROW_PIPELINE:
        rows, step_issues = step(rows, layout, ctx)
        issues += step_issues
    return rows, issues


def spread_hours(hours, capacities):
    """Répartit ``hours`` sur des jours (D-43) : ``capacities`` = [(jour, heures disponibles)] dans
    l'ordre de remplissage. Renvoie [(jour, heures)] ; ``ValueError`` si la capacité ne suffit pas.
    """
    remaining = hours
    spread = []
    for day, available in capacities:
        if remaining <= 0:
            break
        taken = min(available, remaining)
        if taken > 0:
            spread.append((day, taken))
            remaining -= taken
    if remaining > 0:
        raise ValueError(f'Capacité insuffisante : {remaining} h non réparties')
    return spread
