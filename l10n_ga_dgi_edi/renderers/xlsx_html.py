"""Rendu HTML fidèle d'un classeur Excel, base des PDF des déclarations (patron 9).

Le PDF d'une déclaration reproduit son classeur (gabarit officiel rempli ou classeur neuf) :
cellules fusionnées, bordures, largeurs de colonnes, hauteurs de lignes, gras, alignements,
formats numériques. Le tout est mis à l'échelle de la largeur de la page ; la police est
remplacée par une police de rapport lisible (Roboto, fournie par les rapports Odoo), Arial
n'étant pas installée sur le serveur. Aucun accès à l'ORM.
"""

import datetime
import io
from html import escape

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, range_boundaries

FONT_STACK = "Roboto, Lato, 'DejaVu Sans', sans-serif"
DEFAULT_COLUMN_WIDTH = 8.43  # caractères (valeur Excel par défaut)
DEFAULT_ROW_HEIGHT = 15.0  # points
DEFAULT_FONT_SIZE = 11.0
MAX_UPSCALE = 1.35
MIN_VISIBLE_PX = 12
# Bootstrap 5 laisse une bordure visible sur tbody / thead dans wkhtmltopdf (cf. bootstrap_review_report.scss).
NO_BORDER = 'border:0 none !important;'  # en deçà, une cellule dont le texte ne peut pas déborder n'affiche rien
BORDER_STYLES = {
    'hair': '1px solid',
    'thin': '1px solid',
    'dotted': '1px dotted',
    'dashed': '1px dashed',
    'dashDot': '1px dashed',
    'dashDotDot': '1px dashed',
    'mediumDashed': '2px dashed',
    'mediumDashDot': '2px dashed',
    'mediumDashDotDot': '2px dashed',
    'slantDashDot': '2px dashed',
    'medium': '2px solid',
    'thick': '3px solid',
    'double': '3px double',
}
ALIGN = {'centerContinuous': 'center', 'center': 'center', 'right': 'right', 'left': 'left', 'justify': 'justify'}
VALIGN = {'top': 'top', 'center': 'middle', 'bottom': 'bottom'}


def _column_px(width):
    return int((width or DEFAULT_COLUMN_WIDTH) * 7 + 5)  # conversion usuelle caractères → pixels


def _row_px(height):
    return (height or DEFAULT_ROW_HEIGHT) * 96 / 72


def _color(color):
    rgb = getattr(color, 'rgb', None) if color is not None else None
    if isinstance(rgb, str) and len(rgb) == 8 and rgb[:2] != '00':
        return '#' + rgb[2:]
    return None


def _format_number(value, number_format):
    fmt = number_format or 'General'
    if '%' in fmt:
        decimals = fmt.split('.')[1].count('0') if '.' in fmt else 0
        text = f'{value * 100:.{decimals}f} %'
    elif '#,##0' in fmt:
        decimals = fmt.split('.')[1].count('0') if '.' in fmt.split(';')[0] else 0
        text = f'{value:,.{decimals}f}'.replace(',', ' ')
    elif isinstance(value, float) and not value.is_integer():
        text = f'{value:.10g}'
    else:  # format « Standard » : entier sans séparateur de milliers, comme Excel
        text = f'{value:.0f}'
    return text.replace('.', ',')


def _text(cell):
    value = cell.value
    if value is None or cell.data_type == 'f':  # jamais de formule affichée
        return ''
    if isinstance(value, bool):
        return 'VRAI' if value else 'FAUX'
    if isinstance(value, datetime.datetime | datetime.date):
        return f'{value:%d/%m/%Y}'
    if isinstance(value, int | float):
        return _format_number(value, cell.number_format)
    return str(value)


def _border_css(side, edge):
    style = BORDER_STYLES.get(side.style) if side is not None else None
    if not style:
        return ''
    return f'border-{edge}:{style} {_color(side.color) or "#000"} !important;'


def _visible(dimensions, key):
    dimension = dimensions.get(key)
    return not (dimension is not None and dimension.hidden)


def _bounds(sheet):
    area = sheet.print_area
    if area:
        ref = (area[0] if isinstance(area, list | tuple) else area).split('!')[-1].replace('$', '')
        min_col, min_row, max_col, max_row = range_boundaries(ref)
        return min_row, max_row, min_col, max_col
    return 1, sheet.max_row, 1, sheet.max_column


def _frozen_rows(sheet):
    """Nombre de lignes figées en haut de la feuille (volet « A5 » → 4)."""
    pane = sheet.freeze_panes
    if not pane or not pane.startswith('A'):
        return 0
    return max(int(pane[1:]) - 1, 0)


def sheet_to_html(sheet, page_width_px):
    """Tableau HTML d'une feuille, mis à l'échelle de ``page_width_px``."""
    min_row, max_row, min_col, max_col = _bounds(sheet)
    columns = [c for c in range(min_col, max_col + 1) if _visible(sheet.column_dimensions, get_column_letter(c))]
    widths = {c: _column_px(sheet.column_dimensions[get_column_letter(c)].width) for c in columns}
    # Réduction à la largeur de la page ; agrandissement modéré des feuilles étroites (formulaires).
    scale = min(MAX_UPSCALE, page_width_px / max(sum(widths.values()), 1))
    merged, covered = {}, set()
    for merge in sheet.merged_cells.ranges:
        merged[merge.min_row, merge.min_col] = merge
        covered.update(
            (r, c)
            for r in range(merge.min_row, merge.max_row + 1)
            for c in range(merge.min_col, merge.max_col + 1)
            if (r, c) != (merge.min_row, merge.min_col)
        )
    header_rows = _frozen_rows(sheet)  # titre et en-tête répétés sur chaque page (états nominatifs)
    total_width = sum(widths.values()) * scale
    html = [
        # o_ignore_layout_styling : la mise en page des rapports Odoo ne stylise pas ce tableau.
        '<table class="o_l10n_ga_sheet o_ignore_layout_styling table-borderless" '
        'style="table-layout:fixed;border-collapse:collapse;border:0 none !important;'
        f'width:{total_width:.0f}px;font-family:{FONT_STACK};">',
        '<colgroup>',
        *(f'<col style="width:{widths[c] * scale:.1f}px"/>' for c in columns),
        '</colgroup>',
    ]
    for row in range(min_row, max_row + 1):
        if not _visible(sheet.row_dimensions, row):
            continue
        if row == min_row and header_rows:
            html.append(f'<thead style="{NO_BORDER}">')
        if row == min_row + header_rows:
            html.append(f'<tbody style="{NO_BORDER}">')
        height = _row_px(sheet.row_dimensions[row].height) * scale
        html.append(f'<tr style="height:{height:.1f}px;page-break-inside:avoid;border:0 none !important;">')
        for column in columns:
            if (row, column) in covered:
                continue
            html.append(_cell_html(sheet, (row, column), merged.get((row, column)), columns, scale))
        html.append('</tr>')
        if header_rows and row == min_row + header_rows - 1:
            html.append('</thead>')
    html.append('</tbody></table>')
    return ''.join(html)


def _free_right(sheet, row, last_col, columns):
    following = [c for c in columns if c > last_col]
    return not following or sheet.cell(row=row, column=following[0]).value in (None, '')


def _cell_html(sheet, position, merge, columns, scale):
    row, column = position
    cell = sheet.cell(row=row, column=column)
    span = ''
    last_row, last_col = row, column
    if merge:
        last_row, last_col = merge.max_row, merge.max_col
        colspan = len([c for c in columns if column <= c <= last_col])
        rowspan = len([r for r in range(row, last_row + 1) if _visible(sheet.row_dimensions, r)])
        span = f' colspan="{colspan}"' * (colspan > 1) + f' rowspan="{rowspan}"' * (rowspan > 1)
    font = cell.font
    size = (font.sz or DEFAULT_FONT_SIZE) * scale
    text = _text(cell)
    free_right = _free_right(sheet, row, last_col, columns)
    width = sum(
        _column_px(sheet.column_dimensions[get_column_letter(c)].width) for c in columns if column <= c <= last_col
    )
    if not free_right and width * scale < MIN_VISIBLE_PX:
        text = ''  # comme Excel : texte masqué par la cellule voisine remplie
    horizontal = ALIGN.get(cell.alignment.horizontal)
    if not horizontal:
        horizontal = 'right' if isinstance(cell.value, int | float) and not isinstance(cell.value, bool) else 'left'
    style = [
        # Styles des rapports Odoo neutralisés : seules les bordures du classeur sont tracées.
        'border:0 none !important;padding:0 2px !important;line-height:1.15 !important;',
        f'font-size:{size:.2f}pt;',
        'font-weight:bold;' if font.b else '',
        'font-style:italic;' if font.i else '',
        'text-decoration:underline;' if font.u else '',
        f'color:{_color(font.color)};' if _color(font.color) else '',
        f'text-align:{horizontal};',
        f'vertical-align:{VALIGN.get(cell.alignment.vertical, "bottom")};',
        'white-space:normal;word-wrap:break-word;' if cell.alignment.wrap_text else 'white-space:nowrap;',
        # Comme Excel : un texte ne déborde que sur des cellules voisines vides.
        f'overflow:{"visible" if free_right else "hidden"};',
        _border_css(cell.border.left, 'left'),
        _border_css(cell.border.top, 'top'),
        _border_css(sheet.cell(row=row, column=last_col).border.right, 'right'),
        _border_css(sheet.cell(row=last_row, column=column).border.bottom, 'bottom'),
    ]
    fill = cell.fill
    if fill is not None and fill.fill_type == 'solid' and _color(fill.fgColor):
        style.append(f'background-color:{_color(fill.fgColor)};')
    return f'<td{span} style="{"".join(style)}">{escape(text)}</td>'


def workbook_to_html(content, page_width_px):
    """HTML de toutes les feuilles visibles, une par page."""
    book = load_workbook(io.BytesIO(content))
    sheets = [sheet for sheet in book.worksheets if sheet.sheet_state == 'visible']
    parts = []
    for index, sheet in enumerate(sheets):
        page_break = 'page-break-before:always;' if index else ''
        parts.append(
            f'<div class="o_l10n_ga_sheet_page" style="{page_break}">{sheet_to_html(sheet, page_width_px)}</div>'
        )
    return ''.join(parts)
