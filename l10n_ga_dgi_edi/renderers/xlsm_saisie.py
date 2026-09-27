"""Classeurs officiels « edi-annexe-IDxx.xlsm » de la DGI remplis sans les réécrire (D-87, FIX 05).

``openpyxl`` ne sait pas réenregistrer ces classeurs sans perte : boutons de la macro (dessins), listes
déroulantes étendues (x14), propriétés personnalisées disparaissent. Ce module modifie donc directement
le XML de la seule feuille de saisie : chaque autre partie de l'archive (projet VBA, dessins, feuilles
« TradXML » et « Referentiel ») est recopiée octet pour octet.

Seules des valeurs sont écrites (règle d'or 10) : texte en chaîne en ligne, montant et entier en
nombre, date en numéro de série Excel au format date. Une cellule qui porte une formule n'est jamais
touchée. Le classeur recalcule ses formules (totaux, contrôles, colonne XML) à l'ouverture.

Sans dépendance à Odoo : testable seul.
"""

import io
import re
import zipfile
from datetime import date, datetime

from lxml import etree  # pylint: disable=import-error

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'
EXCEL_EPOCH = date(1899, 12, 30)
DATE_NUMFMT_ID = 14  # format intégré « jj/mm/aaaa » (selon la langue du poste)
BUILTIN_DATE_FORMATS = frozenset(range(14, 23)) | frozenset(range(45, 48))
SAISIE_SHEET = 'SAISIE'
_CELL_RE = re.compile(r'^([A-Z]+)(\d+)$')


def _q(tag):
    return f'{{{NS}}}{tag}'


def column_index(letters):
    """« A » → 1, « AG » → 33."""
    index = 0
    for char in letters:
        index = index * 26 + ord(char) - ord('A') + 1
    return index


def _split(ref):
    match = _CELL_RE.match(ref)
    if not match:
        raise ValueError(f'Cellule invalide : {ref}')
    return match.group(1), int(match.group(2))


class SaisieWorkbook:
    """Classeur officiel ouvert pour remplir sa feuille de saisie."""

    def __init__(self, template_bytes, sheet_name=SAISIE_SHEET):
        self._source = template_bytes
        with zipfile.ZipFile(io.BytesIO(template_bytes)) as archive:
            self._sheet_path = self._find_sheet(archive, sheet_name)
            parser = etree.XMLParser(huge_tree=True, remove_blank_text=False)
            self._sheet = etree.fromstring(archive.read(self._sheet_path), parser)
            self._styles = etree.fromstring(archive.read('xl/styles.xml'), parser)
            self._workbook = etree.fromstring(archive.read('xl/workbook.xml'), parser)
        self._sheet_data = self._sheet.find(_q('sheetData'))
        self._rows = {int(row.get('r')): row for row in self._sheet_data.iterfind(_q('row'))}
        self._date_styles = {}

    # --- archive -------------------------------------------------------------------------------

    @staticmethod
    def _find_sheet(archive, sheet_name):
        workbook = etree.fromstring(archive.read('xl/workbook.xml'))
        rels = etree.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = {rel.get('Id'): rel.get('Target') for rel in rels.iterfind(f'{{{PKG_REL_NS}}}Relationship')}
        for sheet in workbook.iter(_q('sheet')):
            if sheet.get('name') == sheet_name:
                target = targets[sheet.get(f'{{{REL_NS}}}id')].lstrip('/')
                return target if target.startswith('xl/') else f'xl/{target}'
        raise ValueError(f'Feuille « {sheet_name} » absente du classeur')

    def build(self):
        """Archive complète : les parties modifiées remplacées, toutes les autres recopiées telles quelles."""
        calc = self._workbook.find(_q('calcPr'))
        if calc is None:
            calc = etree.SubElement(self._workbook, _q('calcPr'))
        calc.set('fullCalcOnLoad', '1')  # totaux et contrôles recalculés à l'ouverture
        replaced = {
            self._sheet_path: etree.tostring(self._sheet, xml_declaration=True, encoding='UTF-8', standalone=True),
            'xl/styles.xml': etree.tostring(self._styles, xml_declaration=True, encoding='UTF-8', standalone=True),
            'xl/workbook.xml': etree.tostring(self._workbook, xml_declaration=True, encoding='UTF-8', standalone=True),
        }
        output = io.BytesIO()
        with (
            zipfile.ZipFile(io.BytesIO(self._source)) as source,
            zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as target,
        ):
            for item in source.infolist():
                data = replaced.get(item.filename)
                target.writestr(item, source.read(item.filename) if data is None else data)
        return output.getvalue()

    # --- styles --------------------------------------------------------------------------------

    def _is_date_style(self, style_index):
        xfs = self._styles.find(_q('cellXfs'))
        if style_index >= len(xfs):
            return False
        num_fmt = int(xfs[style_index].get('numFmtId', 0))
        if num_fmt in BUILTIN_DATE_FORMATS:
            return True
        formats = self._styles.find(_q('numFmts'))
        for fmt in formats.iterfind(_q('numFmt')) if formats is not None else ():
            if int(fmt.get('numFmtId')) == num_fmt:
                code = re.sub(r'"[^"]*"|\[[^\]]*\]', '', fmt.get('formatCode', '')).lower()
                return 'd' in code and 'y' in code
        return False

    def _date_style(self, style_index):
        """Style de la cellule, ou sa copie au format date si elle n'en a pas."""
        if self._is_date_style(style_index):
            return style_index
        if style_index not in self._date_styles:
            xfs = self._styles.find(_q('cellXfs'))
            base = xfs[style_index] if style_index < len(xfs) else xfs[0]
            clone = etree.fromstring(etree.tostring(base))
            clone.set('numFmtId', str(DATE_NUMFMT_ID))
            clone.set('applyNumberFormat', '1')
            xfs.append(clone)
            xfs.set('count', str(len(xfs)))
            self._date_styles[style_index] = len(xfs) - 1
        return self._date_styles[style_index]

    # --- cellules ------------------------------------------------------------------------------

    def _row(self, number):
        row = self._rows.get(number)
        if row is None:
            row = etree.Element(_q('row'), r=str(number))
            following = [r for n, r in self._rows.items() if n > number]
            if following:
                min(following, key=lambda r: int(r.get('r'))).addprevious(row)
            else:
                self._sheet_data.append(row)
            self._rows[number] = row
        return row

    def _cell(self, ref):
        letters, number = _split(ref)
        row = self._row(number)
        position = column_index(letters)
        for cell in row.iterfind(_q('c')):
            other_letters, _other = _split(cell.get('r'))
            other = column_index(other_letters)
            if other == position:
                return cell
            if other > position:
                new = etree.Element(_q('c'), r=ref)
                cell.addprevious(new)
                break
        else:
            new = etree.SubElement(row, _q('c'), r=ref)
        row.attrib.pop('spans', None)  # indication facultative, devenue inexacte
        style = row.get('s')
        if style and row.get('customFormat') == '1':
            new.set('s', style)
        return new

    def put(self, ref, value):
        """Valeur d'une cellule (texte, nombre, date) ; ``None`` ou chaîne vide = cellule vidée."""
        cell = self._cell(ref)
        if cell.find(_q('f')) is not None:
            raise ValueError(f'La cellule {ref} porte une formule du classeur officiel : jamais écrasée')
        for child in list(cell):
            cell.remove(child)
        cell.attrib.pop('t', None)
        if value is None or value is False or value == '':
            return
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            cell.set('s', str(self._date_style(int(cell.get('s', 0)))))
            etree.SubElement(cell, _q('v')).text = str((value - EXCEL_EPOCH).days)
        elif isinstance(value, bool):
            raise ValueError(f'Valeur booléenne non prévue en {ref}')
        elif isinstance(value, (int, float)):
            number = float(value)
            etree.SubElement(cell, _q('v')).text = str(int(number)) if number.is_integer() else repr(number)
        else:
            text = str(value)
            cell.set('t', 'inlineStr')
            node = etree.SubElement(etree.SubElement(cell, _q('is')), _q('t'))
            node.text = text
            if text != text.strip():
                node.set(XML_SPACE, 'preserve')

    def value(self, ref):
        """Valeur écrite ou lue (texte en ligne, partagé non résolu, nombre) — contrôles et tests."""
        letters, number = _split(ref)
        row = self._rows.get(number)
        if row is None:
            return None
        for cell in row.iterfind(_q('c')):
            if cell.get('r') == f'{letters}{number}':
                if cell.get('t') == 'inlineStr':
                    return ''.join(cell.itertext())
                node = cell.find(_q('v'))
                return None if node is None else node.text
        return None

    def fill(self, header, first_row, rows):
        """En-tête ``{référence: valeur}`` puis lignes ``[{lettre de colonne: valeur}]`` dès ``first_row``."""
        for ref, value in header.items():
            self.put(ref, value)
        for offset, row in enumerate(rows):
            for letters, value in row.items():
                self.put(f'{letters}{first_row + offset}', value)
        return self
