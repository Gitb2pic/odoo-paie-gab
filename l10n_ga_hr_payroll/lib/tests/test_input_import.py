"""Import des variables du mois (F3, patron 13) : filtres purs du pipeline."""

import pytest
from ga_fiscal_core import input_import as ii

CTX = ii.ImportContext(
    columns={'GA_TRANSP': (ii.AMOUNT, 11), 'GA_PRIME': (ii.AMOUNT, 12), 'GA_HS_J': (ii.HOURS, 21)},
    employees_by_ref={'M001': 1, 'M002': 2, '42': 3, 'M009': 9},
    employees_by_name={'Awa Ndong': (1,), 'Paul Mba': (2,), 'Homonyme': (4, 5)},
    batch=frozenset({1, 2, 3, 4}),
)
HEADER = ('Matricule', 'Salarié', 'GA_TRANSP — Prime de transport', 'GA_HS_J — Heures sup. jour')


def _run(rows, header=HEADER):
    return ii.run(header, list(enumerate(rows, start=2)), CTX)


def _codes(issues):
    return [issue.code for issue in issues]


# --- en-têtes -----------------------------------------------------------------------------------


def test_normalise_headers_splits_code_and_label():
    normalised, issues = ii.normalise_headers(HEADER)
    assert issues == ()
    assert normalised.key_index == 0
    assert normalised.name_index == 1
    assert normalised.columns == ((2, 'GA_TRANSP'), (3, 'GA_HS_J'))


def test_normalise_headers_missing_key_is_fatal():
    normalised, issues = ii.normalise_headers(('Salarié', 'GA_TRANSP'))
    assert normalised is None
    assert _codes(issues) == [ii.MISSING_KEY_COLUMN]
    assert issues[0].fatal


def test_normalise_headers_duplicate_column_ignored():
    normalised, issues = ii.normalise_headers(('matricule', 'GA_TRANSP', 'GA_TRANSP — bis', None, ''))
    assert normalised.columns == ()
    assert _codes(issues) == [ii.DUPLICATE_COLUMN]
    assert issues[0].column == 'GA_TRANSP'


def test_resolve_columns_unknown_column_ignored():
    normalised, _issues = ii.normalise_headers(('Matricule', 'GA_TRANSP', 'GA_INCONNU — ?'))
    layout, issues = ii.resolve_columns(normalised, CTX)
    assert [column.code for column in layout.columns] == ['GA_TRANSP']
    assert layout.columns[0] == ii.Column(1, 'GA_TRANSP', ii.AMOUNT, 11)
    assert _codes(issues) == [ii.UNKNOWN_COLUMN]


def test_run_stops_on_fatal_header():
    rows, issues = _run([('M001', 'Awa', 1000)], header=('Nom', 'GA_TRANSP'))
    assert rows == ()
    assert _codes(issues) == [ii.MISSING_KEY_COLUMN]


# --- salarié ------------------------------------------------------------------------------------


def test_resolve_employee_by_reference_numeric_cell_and_name_fallback():
    rows, issues = _run([('M001', 'x', 1), (42.0, 'y', 1), (None, 'Paul Mba', 1), ('  M002 ', '', 2)])
    # M002 apparaît deux fois (ligne 4 par le nom, ligne 5 par le matricule) : doublon.
    assert [row.employee for row in rows] == [1, 3]
    assert _codes(issues) == [ii.DUPLICATE_EMPLOYEE, ii.DUPLICATE_EMPLOYEE]


def test_resolve_employee_unknown_or_ambiguous():
    rows, issues = _run([('M404', 'Awa Ndong', 1), (None, 'Homonyme', 1), (None, None, 1), ('M001', '', 5)])
    assert [row.employee for row in rows] == [1]
    assert _codes(issues) == [ii.UNKNOWN_EMPLOYEE] * 3
    assert [issue.row for issue in issues] == [2, 3, 4]
    assert issues[0].value == 'M404'


def test_check_in_batch():
    rows, issues = _run([('M009', '', 1), ('M001', '', 1)])
    assert [row.employee for row in rows] == [1]
    assert _codes(issues) == [ii.NOT_IN_BATCH]


def test_empty_rows_are_skipped():
    rows, issues = _run([(None, None, None, None), ('', ' ', None), ('M001', '', 1)])
    assert [row.row for row in rows] == [4]
    assert issues == ()


# --- montants -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        (15000, 15000.0),
        (7.5, 7.5),
        ('1 500', 1500.0),
        ('12,5', 12.5),
        (' 2 000,25 ', 2000.25),
        (0, 0.0),
    ],
)
def test_parse_number(raw, expected):
    assert ii.parse_number(raw) == expected


@pytest.mark.parametrize('raw', ['abc', '1.2.3', True, 'nan', 'inf', object()])
def test_parse_number_invalid(raw):
    with pytest.raises(ValueError):
        ii.parse_number(raw)


def test_parse_amounts_values_and_empty_cells():
    rows, issues = _run([('M001', '', '25 000', 7.5), ('M002', '', None, ''), ('42', '', 0, None)])
    assert issues == ()
    assert rows[0].values == (('GA_TRANSP', 25000.0), ('GA_HS_J', 7.5))
    assert rows[1].values == ()  # vide = inchangé
    assert rows[2].values == (('GA_TRANSP', 0.0),)  # 0 = supprime


def test_wrong_row_rejected_without_blocking_good_rows():
    rows, issues = _run([('M001', '', 'mille', 2), ('M002', '', -5, None), ('42', '', 1000, 1.25)])
    assert [row.employee for row in rows] == [3]
    assert _codes(issues) == [ii.INVALID_NUMBER, ii.NEGATIVE_NUMBER]
    assert (issues[0].row, issues[0].column, issues[0].value) == (2, 'GA_TRANSP', 'mille')
    assert (issues[1].row, issues[1].column) == (3, 'GA_TRANSP')


def test_short_row_is_padded():
    rows, issues = _run([('M001',)])
    assert issues == ()
    assert rows[0].values == ()


def test_pipeline_is_the_documented_sequence():
    assert [step.__name__ for step in ii.ROW_PIPELINE] == [
        'resolve_employee',
        'check_in_batch',
        'dedupe',
        'parse_amounts',
    ]


# --- répartition des heures (D-43) --------------------------------------------------------------


def test_spread_hours_fills_days_in_order():
    capacities = [('d30', 16), ('d29', 24), ('d28', 0), ('d27', 16)]
    assert ii.spread_hours(7.5, capacities) == [('d30', 7.5)]
    assert ii.spread_hours(30.25, capacities) == [('d30', 16), ('d29', 14.25)]
    assert ii.spread_hours(56, capacities) == [('d30', 16), ('d29', 24), ('d27', 16)]
    assert ii.spread_hours(0, capacities) == []


def test_spread_hours_capacity_exceeded():
    with pytest.raises(ValueError):
        ii.spread_hours(57, [('d30', 16), ('d29', 24), ('d27', 16)])
