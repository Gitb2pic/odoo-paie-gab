"""Classeur neuf d'une déclaration sans gabarit officiel (DTS…) : ``xlsxwriter``, valeurs uniquement.

Mise en forme d'un imprimé : titre, bloc d'identification encadré, récapitulatif des cases (lignes
de total en gras), état nominatif avec titre et en-tête répétés à l'impression et ligne de total.
Police Arial, montants au format « # ##0 », dates JJ/MM/AAAA. Le PDF de la déclaration est le rendu
de ce classeur (``xlsx_html``).
"""

import datetime
import io

import xlsxwriter

from .base import DeclarationBuilder

FONT = 'Arial'
AMOUNT = '#,##0'
SHEET_NAME_MAX = 31
MIN_WIDTH, MAX_WIDTH, HEADER_WRAP = 6, 70, 14
PAPER_A4, PAPER_A3 = 9, 8  # codes de format xlsxwriter
GREY = '#D9D9D9'
LIGHT = '#F2F2F2'


class XlsxDeclarationBuilder(DeclarationBuilder):
    def __init__(self, title='', subtitle=''):
        self._stream = io.BytesIO()
        self._book = xlsxwriter.Workbook(self._stream, {'in_memory': True})
        self._title, self._subtitle = title, subtitle
        self._header = []
        base = {'font_name': FONT, 'font_size': 10, 'valign': 'vcenter'}
        grid = {**base, 'border': 1}
        formats = {
            'title': {**base, 'bold': True, 'font_size': 14},
            'subtitle': {**base, 'italic': True, 'font_color': '#555555'},
            'section': {**base, 'bold': True, 'font_size': 11},
            'label': {**grid, 'bold': True, 'bg_color': LIGHT},
            'head': {**grid, 'bold': True, 'bg_color': GREY, 'text_wrap': True, 'align': 'center'},
            'cell': grid,
            'amount': {**grid, 'num_format': AMOUNT},
            'number': {**grid, 'num_format': '0.######'},
            'date': {**grid, 'num_format': 'dd/mm/yyyy', 'align': 'center'},
        }
        self._f = {name: self._book.add_format(spec) for name, spec in formats.items()}
        for name in ('cell', 'amount', 'number', 'date'):
            self._f[f'{name}_bold'] = self._book.add_format({**formats[name], 'bold': True, 'bg_color': LIGHT})

    # --- écriture typée (jamais de formule : les chaînes restent des chaînes) ------------------

    def _write(self, sheet, row, column, value, *, kind='cell', bold=False):
        def fmt(name):
            return self._f[f'{name}_bold' if bold and f'{name}_bold' in self._f else name]

        if value is None or value is False or value == '':
            sheet.write_blank(row, column, None, fmt(kind))
        elif isinstance(value, bool):
            sheet.write_string(row, column, str(value), fmt(kind))
        elif isinstance(value, int | float):
            numeric = (
                kind
                if kind in ('title', 'section', 'label', 'head')
                else ('amount' if float(value).is_integer() else 'number')
            )
            sheet.write_number(row, column, value, fmt(numeric))
        elif isinstance(value, datetime.date):
            sheet.write_datetime(row, column, datetime.datetime.combine(value, datetime.time()), fmt('date'))
        else:
            sheet.write_string(row, column, str(value), fmt(kind))

    @staticmethod
    def _text_length(value):
        if isinstance(value, int | float) and not isinstance(value, bool):
            return len(f'{value:,.0f}')
        if isinstance(value, datetime.date):
            return 10
        return len(str(value or ''))

    def _widths(self, headers, rows):
        # L'en-tête passe à la ligne : il n'impose que la longueur de son plus long mot.
        widths = {
            column: min(HEADER_WRAP, max((len(word) for word in str(header).split()), default=0))
            for column, header in enumerate(headers)
        }
        for row in rows:
            for column, value in enumerate(row):
                widths[column] = max(widths.get(column, 0), self._text_length(value))
        return {column: max(MIN_WIDTH, min(MAX_WIDTH, width + 2)) for column, width in widths.items()}

    def _sheet(self, name, landscape=False, paper=PAPER_A4):
        sheet = self._book.add_worksheet(str(name)[:SHEET_NAME_MAX])
        sheet.set_paper(paper)
        if landscape:
            sheet.set_landscape()
        sheet.fit_to_pages(1, 0)
        sheet.set_margins(0.3, 0.3, 0.4, 0.4)
        sheet.hide_gridlines(2)
        return sheet

    def _titles(self, sheet, line, title, subtitle):
        if title:
            sheet.set_row(line, 24)
            self._write(sheet, line, 0, title, kind='title')
            line += 1
        if subtitle:
            self._write(sheet, line, 0, subtitle, kind='subtitle')
            line += 1
        return line + 1

    # --- interface Builder ---------------------------------------------------------------------

    def header(self, values):
        """Bloc d'identification : ``{libellé: valeur}``."""
        self._header = [(str(label), value) for label, value in values.items()]

    def boxes(self, headers, rows, bold=()):  # pylint: disable=arguments-differ
        """Feuille « Déclaration » : titre, identification, récapitulatif des cases.

        ``rows`` : ``[(code, désignation, valeur)]`` ; ``bold`` : codes des lignes de total.
        """
        sheet = self._sheet('Déclaration')
        rows = [list(row) for row in rows]
        widths = self._widths(headers, rows)
        widths[0] = max(widths.get(0, MIN_WIDTH), *(len(label) + 2 for label, _value in self._header), MIN_WIDTH)
        widths[1] = max(widths.get(1, MIN_WIDTH), 48)
        for column, width in widths.items():
            sheet.set_column(column, column, width)
        line = self._titles(sheet, 0, self._title, self._subtitle)
        if self._header:
            self._write(sheet, line, 0, 'Identification', kind='section')
            line += 1
            for label, value in self._header:
                self._write(sheet, line, 0, label, kind='label')
                sheet.merge_range(line, 1, line, len(headers) - 1, None, self._f['cell'])
                self._write(sheet, line, 1, value)
                line += 1
            line += 1
        self._write(sheet, line, 0, 'Récapitulatif', kind='section')
        line += 1
        for column, value in enumerate(headers):
            self._write(sheet, line, column, value, kind='head')
        for row in rows:
            line += 1
            for column, value in enumerate(row):
                self._write(sheet, line, column, value, bold=row[0] in bold)

    def table(self, sheet, start_row, rows, headers=(), *, title='', totals=None):  # pylint: disable=arguments-differ
        """État nominatif (paysage) : titre et en-tête grisé répétés à l'impression, ligne de total.

        ``totals`` : ligne de total (même nombre de colonnes que ``headers``) ou ``None``.
        """
        worksheet = self._sheet(sheet, landscape=True)
        rows = [list(row) for row in rows]
        for column, width in self._widths(headers, [*rows, *([totals] if totals else [])]).items():
            worksheet.set_column(column, column, width)
        line = self._titles(worksheet, start_row, title, '')
        if headers:
            worksheet.set_row(line, 42)
            for column, value in enumerate(headers):
                self._write(worksheet, line, column, value, kind='head')
            worksheet.freeze_panes(line + 1, 0)
            worksheet.repeat_rows(start_row, line)
            line += 1
        for row in rows:
            for column, value in enumerate(row):
                self._write(worksheet, line, column, value)
            line += 1
        if totals:
            for column, value in enumerate(totals):
                self._write(worksheet, line, column, value, bold=True)

    def form(self, name, blocks, *, title='', subtitle='', landscape=False, paper=PAPER_A4):
        """Feuille d'imprimé composée de blocs, dans l'ordre :

        - ``{'title': str, 'pairs': [(libellé, valeur)]}`` : bloc d'identification ;
        - ``{'title': str, 'headers': [...], 'rows': [[...]], 'totals': [...] | None, 'bold': {index}}`` :
          tableau encadré (lignes ``bold`` en gras) ;
        - ``{'text': str}`` : paragraphe (note explicative).

        Largeurs de colonnes : maximum des blocs ; en-tête de tableau grisé.
        """
        sheet = self._sheet(name, landscape=landscape, paper=paper)
        widths = self._form_widths(blocks)
        span = max(widths) if widths else 1
        for column, width in widths.items():
            sheet.set_column(column, column, width)
        line = self._titles(sheet, 0, title, subtitle)
        for block in blocks:
            if block.get('title'):
                self._write(sheet, line, 0, block['title'], kind='section')
                line += 1
            if 'pairs' in block:
                line = self._form_pairs(sheet, line, block['pairs'], span)
            elif 'headers' in block:
                line = self._form_table(sheet, line, block)
            elif 'text' in block:
                self._write(sheet, line, 0, block['text'], kind='subtitle')
                line += 1
            line += 1
        return sheet

    def _form_widths(self, blocks):
        widths = {}
        for block in blocks:
            if 'headers' in block:
                rows = [*block['rows'], *([block['totals']] if block.get('totals') else [])]
                for column, width in self._widths(block['headers'], rows).items():
                    widths[column] = max(widths.get(column, 0), width)
            elif 'pairs' in block:
                widths[0] = max(widths.get(0, MIN_WIDTH), *(len(str(label)) + 2 for label, _v in block['pairs']))
        pairs = [pair for block in blocks for pair in block.get('pairs', [])]
        if pairs:  # la valeur d'un couple occupe les colonnes suivantes : elles doivent pouvoir la contenir
            needed = max(self._text_length(value) for _label, value in pairs) + 2
            others = [column for column in widths if column]
            available = sum(widths[column] for column in others)
            if available < needed:
                target = others[-1] if others else 1
                widths[target] = widths.get(target, MIN_WIDTH) + needed - available
        return widths

    def _form_pairs(self, sheet, line, pairs, span):
        for label, value in pairs:
            self._write(sheet, line, 0, label, kind='label')
            if span > 1:
                sheet.merge_range(line, 1, line, span, None, self._f['cell'])
            self._write(sheet, line, 1, value)
            line += 1
        return line

    def _form_table(self, sheet, line, block):
        sheet.set_row(line, 30)
        for column, value in enumerate(block['headers']):
            self._write(sheet, line, column, value, kind='head')
        line += 1
        bold = block.get('bold', set())
        for index, row in enumerate(block['rows']):
            for column, value in enumerate(row):
                self._write(sheet, line, column, value, bold=index in bold)
            line += 1
        if block.get('totals'):
            for column, value in enumerate(block['totals']):
                self._write(sheet, line, column, value, bold=True)
            line += 1
        return line

    def build(self):
        self._book.close()
        return self._stream.getvalue()
