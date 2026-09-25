"""Classeur neuf d'une déclaration (``xlsxwriter``) : feuilles « Déclaration » et « Détails »."""

from odoo.addons.l10n_ga_hr_payroll.report.xlsx_renderer import XlsxRenderer

from .base import DeclarationBuilder


class XlsxDeclarationBuilder(DeclarationBuilder):
    """Réutilise le constructeur des états de paie (valeurs typées, chaînes jamais interprétées en formule)."""

    def __init__(self):
        self._renderer = XlsxRenderer()
        self._header = []

    def header(self, values):
        self._header = [(str(label), value) for label, value in values.items()]

    def boxes(self, headers, rows):  # pylint: disable=arguments-differ
        """Feuille « Déclaration » : en-tête puis une ligne par case."""
        rows = [*([label, value] for label, value in self._header), [], list(headers), *(list(row) for row in rows)]
        self._renderer.add_sheet('Déclaration', [], rows)

    def table(self, sheet, start_row, rows, headers=()):
        self._renderer.add_sheet(sheet, list(headers), [*([] for _ in range(start_row)), *(list(row) for row in rows)])

    def build(self):
        return self._renderer.build()
