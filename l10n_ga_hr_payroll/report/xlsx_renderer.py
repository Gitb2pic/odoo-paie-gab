"""Constructeur des états Excel neufs (patron 9 « Builder », F10, F13, règle d'or 10).

``xlsxwriter`` en ``constant_memory`` (gros volumes) : chaque feuille est écrite ligne par ligne,
d'un seul tenant ; les totaux sont calculés en Python et écrits comme **valeurs**, jamais comme
formules. Les classeurs officiels ``.xlsm`` de la DGI auront leur propre moteur (``openpyxl``,
étape 4) derrière la même interface ``add_sheet`` / ``build``.
"""

import io
import re

import xlsxwriter

SHEET_NAME_MAX = 31  # limite Excel d'un nom de feuille
SHEET_FORBIDDEN = re.compile(r'[\[\]:*?/\\]')
AMOUNT_FORMAT = '#,##0'
COLUMN_WIDTH = 16


class XlsxRenderer:
    def __init__(self):
        self._stream = io.BytesIO()
        self._book = xlsxwriter.Workbook(self._stream, {'constant_memory': True})
        self._bold = self._book.add_format({'bold': True})
        self._amount = self._book.add_format({'num_format': AMOUNT_FORMAT})
        self._amount_bold = self._book.add_format({'num_format': AMOUNT_FORMAT, 'bold': True})
        self._names = set()

    def _sheet_name(self, name):
        base = SHEET_FORBIDDEN.sub(' ', str(name or '-')).strip()[:SHEET_NAME_MAX] or '-'
        candidate, index = base, 1
        while candidate.lower() in self._names:
            index += 1
            suffix = f' ({index})'
            candidate = base[: SHEET_NAME_MAX - len(suffix)] + suffix
        self._names.add(candidate.lower())
        return candidate

    def _write_row(self, sheet, row, values, bold=False):
        for column, value in enumerate(values):
            if isinstance(value, bool) or value is None:
                sheet.write_blank(row, column, None)
            elif isinstance(value, int | float):
                sheet.write_number(row, column, value, self._amount_bold if bold else self._amount)
            else:
                sheet.write_string(row, column, str(value), self._bold if bold else None)

    def add_sheet(self, name, headers, rows, totals=()):
        """Feuille : en-têtes, lignes de valeurs, puis lignes de totaux (en gras)."""
        sheet = self._book.add_worksheet(self._sheet_name(name))
        sheet.freeze_panes(1, 0)
        sheet.set_column(0, max(len(headers) - 1, 0), COLUMN_WIDTH)
        self._write_row(sheet, 0, headers, bold=True)
        row = 0
        for row, values in enumerate(rows, start=1):
            self._write_row(sheet, row, values)
        for offset, values in enumerate(totals, start=1):
            self._write_row(sheet, row + offset, values, bold=True)
        return sheet

    def build(self):
        self._book.close()
        return self._stream.getvalue()
