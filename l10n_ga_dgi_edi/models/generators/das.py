"""DAS annuelle : ID19, ID20, ID21, ID22 (base 06 §3, art. 167 ter CGI ; plan 4.4).

Les colonnes et leurs sources sont en données (cases du type ``DAS``) ; ce générateur ajoute :
le détail nominatif (ID21, une ligne par salarié), les cumuls d'ouverture de l'année (F12),
les tranches de l'ID20, l'éligibilité à l'ID19, les quittances de l'année (ID22) et les contrôles
de rapprochement avec les ID10. Le classeur (ID20, ID21 paginé, ID22, ID19) est rendu à partir des
seules valeurs figées de la déclaration.
"""

from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import models
from odoo.tools import float_compare, float_round
from odoo.tools.misc import file_open

from ...renderers.xlsm_saisie import SaisieWorkbook
from ...renderers.xlsx_builder import PAPER_A3, SHEET_NAME_MAX, XlsxDeclarationBuilder
from ..declaration_generator import BLOCKING, WARNING

# Cases calculées par ce générateur (les autres cases sont alimentées par leurs sources en données).
EMPLOYEES, ID19_COUNT = 'EMPLOYEES', 'ID19_COUNT'
ID20 = {'A': ('ID20_A_COUNT', 'ID20_A_TOTAL'), 'B': ('ID20_B_COUNT', 'ID20_B_TOTAL')}
PAYMENT_BOXES = {'rs': 'PAID_RS', 'fnh': 'PAID_FNH', 'cfp': 'PAID_CFP', 'other': 'PAID_OTHER'}
PRESENCE_NET = 'presence_net'  # cadre des termes « nets des cotisations » (option société, point 09-6)
ID21_SECTIONS = ('id21', PRESENCE_NET)
ID19_GAINS = ('C1', 'C5', 'C4', 'C2', 'C3')  # présence, congés, indemnités, avantages, nourriture
NET_OPENING_FIELDS = {'contributions'}
TOTAL_BOX, TAXES_BOX, EXEMPT_BOX = 'C6', 'C11', 'NT_TOTAL'
PAYMENT_TYPES = ('ID10', 'ID28')
MARITAL = {'married': '1', 'single': '2', 'cohabitant': '2', 'widower': '3', 'divorced': '4'}
GENDER = {'male': '1', 'female': '2'}

# --- classeurs officiels « edi-annexe » de la DGI (D-87, FIX 05) ---------------------------------------
# Mise en page des classeurs (feuille SAISIE) et libellés exacts de leurs listes (feuille Referentiel) :
# des données de présentation, pas des règles fiscales ; vérifiées sur les gabarits par les tests.
OFFICIAL_TEMPLATES = {
    # code : (gabarit, première ligne de données, lignes couvertes par les formules du classeur)
    'ID19': ('l10n_ga_dgi_edi/static/templates/edi-annexe-ID19.xlsm', 18, 1997),
    'ID21': ('l10n_ga_dgi_edi/static/templates/edi-annexe-ID21.xlsm', 18, 3001),
}
HEADER_CELLS = ('C9', 'C11', 'C13')  # NIF du déclarant, exercice, période
ANNUAL = 'Annuel'
# codes DAS de la charge utile → libellés des listes du classeur ID21
ID21_NATIONALITY = {'1': 'Gabonais', '2': 'CEMAC', '3': 'Autres africains', '4': 'Non africains'}
ID21_GENDER = {'1': 'Masculin', '2': 'Féminin'}
ID21_MARITAL = {'1': 'Marié', '2': 'Celibataire', '3': 'Veuf', '4': 'Divorcé'}
# ID19 : le régime matrimonial n'est pas connu d'Odoo → communauté de biens par défaut (D-113)
ID19_MARITAL = {
    '1': 'Marié(e) en régime de communauté de biens',
    '2': 'Célibataire',
    '3': 'Veuf(ve)',
    '4': 'Divorcé(e)',
}
ID19_MARITAL_UNKNOWN = 'Non précisé'
ID19_NATURES = {
    'presence': 'Présence - Montant versé (après déduction des retenues pour retraite et sécurité sociale '
    'et avant déduction des retenues pour logement, nourriture etc)',
    'leave': 'Congés - Montant versé (après déduction des retenues pour retraite et sécurité sociale '
    'et avant déduction des retenues pour logement, nourriture etc)',
    'housing': 'Avantage en nature : logement',
    'utilities': 'Avantage en nature :  eau, electricité',
    'domestic': 'Avantage en nature :  domesticité',
    'food': 'Avantage en nature :  nourriture',
    'tcs': "Taxe complémentaire à déduire pour l'année",
    'irpp': "IRPP retenu pour l'année",
    'exempt': "Montant des indemnités (non imposable)  lors qu'elle n'est pas reversée en numéraire",
}
# avantages en nature : clé de la charge utile, rubriques de paie, paramètre du taux d'évaluation (art. 93)
AIK_KINDS = (
    ('housing', 'aik_housing', ('GA_AN_LOGT',), 'l10n_ga_aik_housing_rate'),
    ('utilities', 'aik_utilities', ('GA_AN_EAU',), 'l10n_ga_aik_utilities_rate'),
    ('domestic', 'aik_domestic', ('GA_AN_DOM',), 'l10n_ga_aik_domestic_rate'),
)
FOOD_RATE = 'l10n_ga_aik_food_rate'
BENEFIT_BOX, FOOD_BOX = 'C2', 'C3'


class L10nGaDeclarationGeneratorDas(models.AbstractModel):
    _name = 'l10n_ga.declaration.generator.das'
    _inherit = 'l10n_ga.declaration.generator.payslip'
    _description = 'DAS — déclaration annuelle des salaires (ID19 à ID22)'

    # --- paramètres et options --------------------------------------------------------------

    def _parameter(self, declaration, code):
        return (
            self.env['hr.rule.parameter']
            .sudo()
            ._get_parameter_from_code(code, declaration.date_to, raise_if_not_found=False)
        )

    def _required_parameters(self, declaration):
        return sorted(
            {
                *super()._required_parameters(declaration),
                'l10n_ga_das_id19_threshold',
                'l10n_ga_das_id20_threshold',
                'l10n_ga_das_id21_lines',
            }
        )

    def _net_of_contributions(self, declaration):
        return declaration.company_id.l10n_ga_das_presence_net

    def _sign(self, box, fact, declaration=None):
        if box.section == PRESENCE_NET and declaration and not self._net_of_contributions(declaration):
            codes = dict(box._source_codes())
            if fact['code'] in codes:
                return 0  # colonne (1) déclarée brute : cotisations non déduites
        return super()._sign(box, fact, declaration)

    # --- collecte ---------------------------------------------------------------------------

    def _collect(self, declaration):
        facts = super()._collect(declaration)
        facts['openings'] = self.env['l10n_ga.ytd.opening'].search(
            [('company_id', '=', declaration.company_id.id), ('year', '=', declaration.date_to.year)]
        )
        facts['payments'] = self._year_payments(declaration)
        return facts

    def _year_declarations(self, declaration, codes):
        """Déclarations actives de l'année par période : la dernière rectificative remplace l'originale."""
        found = self.env['l10n_ga.declaration'].search(
            [
                ('company_id', '=', declaration.company_id.id),
                ('type_id.code', 'in', list(codes)),
                ('date_from', '>=', declaration.date_from),
                ('date_to', '<=', declaration.date_to),
                ('state', '!=', 'cancel'),
            ],
            order='id',
        )
        latest = {}
        for decl in found:
            latest[decl.type_id.code, decl.date_from] = decl  # les rectificatives sont créées après
        return self.env['l10n_ga.declaration'].concat(*latest.values())

    def _year_payments(self, declaration):
        return self._year_declarations(declaration, PAYMENT_TYPES).payment_ids.sorted(
            lambda p: (p.declaration_id.date_from, p.date, p.id)
        )

    def _contributions(self, declaration, facts):
        contributions = super()._contributions(declaration, facts)
        months = self._month_count(declaration)
        net = self._net_of_contributions(declaration)
        for box in self._boxes(declaration).filtered('opening_fields'):
            per_employee = contributions.setdefault(box.code, {})
            for opening in facts.get('openings', []):
                value = sum(
                    sign * opening[field]
                    for field, sign in box._opening_fields()
                    if net or box.section != PRESENCE_NET or field not in NET_OPENING_FIELDS
                )
                item = per_employee.setdefault(
                    opening.employee_id,
                    {'amount': 0.0, 'lines': self.env['hr.payslip.line'], 'months': [0.0] * months},
                )
                item['amount'] += value
        return contributions

    # --- détail nominatif (ID21) ------------------------------------------------------------

    def _employee_boxes(self, declaration):
        """Colonnes de l'ID21 (cadres ``id21`` et ``presence_net`` des données)."""
        return self._boxes(declaration).filtered(lambda b: b.section in ID21_SECTIONS)

    def _months_paid(self, declaration, facts, employee):
        """Mois de l'année payés au salarié (bulletins et période du cumul d'ouverture)."""
        months = {self._month_index(declaration, slip) for slip in facts['slips'] if slip.employee_id == employee}
        for opening in facts['openings'].filtered(lambda o: o.employee_id == employee):
            day = max(opening.date_from, declaration.date_from)
            while day <= min(opening.date_to, declaration.date_to):
                months.add(self._month_of(declaration, day))
                day += relativedelta(months=1, day=1)
        return len(months)

    def _employee_rows(self, declaration, facts):
        contributions = self._contributions(declaration, facts)
        boxes = self._employee_boxes(declaration)
        employees = {e for per_employee in contributions.values() for e in per_employee}
        rows = []
        for employee in sorted(employees, key=lambda e: (e.name or '', e.id)):
            values = {}
            for box in boxes:
                if box.sum_box_codes:
                    values[box.code] = sum(sign * values.get(code, 0.0) for code, sign in box._sum_box_codes())
                else:
                    item = contributions.get(box.code, {}).get(employee)
                    values[box.code] = float_round(item['amount'] if item else 0.0, precision_digits=0)
            rows.append((employee, values))
        return rows

    def _identity(self, declaration, facts, employee):
        slips = facts['slips'].filtered(lambda s: s.employee_id == employee).sorted('date_to')
        last = slips[-1:]
        version = last.version_id or employee.version_id
        start = max(version.contract_date_start or declaration.date_from, declaration.date_from)
        end_date = version.departure_date or version.contract_date_end
        end = min(end_date, declaration.date_to) if end_date else declaration.date_to
        birthday = employee.birthday
        new_year = date(declaration.date_to.year, 1, 1)
        age = relativedelta(new_year, birthday).years if birthday else ''
        return {
            'registration': last.l10n_ga_registration_number or employee.registration_number or '',
            'number': last.l10n_ga_ssnid or version.ssnid or '',
            'nif': last.l10n_ga_nif or version.l10n_ga_nif or '',
            'name': last.l10n_ga_employee_name or employee.name,
            'job': last.l10n_ga_job_title or employee.job_title or '',
            'job_code': version.l10n_ga_job_code or '',
            'level_code': version.l10n_ga_level_code or '',
            'nationality': version.l10n_ga_nationality_code or '',
            'age': age,
            'gender': GENDER.get(employee.sex or '', ''),
            'marital': MARITAL.get(last.l10n_ga_marital_used or version.marital or '', ''),
            'children': last.l10n_ga_children_used if last else version.children,
            'period': f'{start:%d/%m} – {end:%d/%m}',
            'date_start': str(start),
            'date_end': str(end),
            'phone': employee.private_phone or '',
            'street': version.private_street or '',
            'city': version.private_city or '',
        }

    @staticmethod
    def _benefits_by_kind(slips, total):
        """Avantages logement / eau-électricité / domesticité par nature (ID19) ; le reste de la colonne (2)
        (cumuls d'ouverture, sans ventilation) est rattaché au logement."""
        split = {
            key: float_round(sum(slips.line_ids.filtered(lambda line, c=codes: line.code in c).mapped('total')), 0)
            for _kind, key, codes, _rate in AIK_KINDS
        }
        split[AIK_KINDS[0][1]] += (total or 0.0) - sum(split.values())
        return split

    def _details(self, declaration, facts):
        id19 = self._parameter(declaration, 'l10n_ga_das_id19_threshold') or 0.0
        id20 = self._parameter(declaration, 'l10n_ga_das_id20_threshold') or 0.0
        with_exempt = declaration.company_id.l10n_ga_das_average_basis == 'all'
        details = []
        for employee, values in self._employee_rows(declaration, facts):
            months = self._months_paid(declaration, facts, employee) or 1
            base = values.get(TOTAL_BOX, 0.0) + (values.get(EXEMPT_BOX, 0.0) if with_exempt else 0.0)
            average = float_round(base / months, precision_digits=0)
            slips = facts['slips'].filtered(lambda s, e=employee: s.employee_id == e)
            payload = {
                **self._identity(declaration, facts, employee),
                **values,
                **self._benefits_by_kind(slips, values.get(BENEFIT_BOX)),
                'months': months,
                'average': average,
                'tranche': 'A' if float_compare(average, id20, precision_digits=0) >= 0 else 'B',
                'id19': float_compare(average, id19, precision_digits=0) > 0,
            }
            details.append(
                {
                    'employee_id': employee.id,
                    'label': payload['name'],
                    'amount': values.get(TOTAL_BOX, 0.0),
                    'payload': payload,
                    'payslip_line_ids': facts['slips'].filtered(lambda s, e=employee: s.employee_id == e).line_ids.ids,
                }
            )
        for payment in facts['payments']:
            details.append(
                {
                    'box_code': PAYMENT_BOXES[payment.kind],
                    'label': payment.receipt_number,
                    'amount': payment.amount,
                    'payload': {
                        'month': f'{payment.declaration_id.date_from:%m/%Y}',
                        'declaration': payment.declaration_id.name,
                        'date': str(payment.date),
                        'number': payment.receipt_number,
                        'kind': payment.kind,
                    },
                }
            )
        return details

    def _fill(self, declaration, facts):
        values = super()._fill(declaration, facts)
        details = self._details(declaration, facts)
        rows = [detail['payload'] for detail in details if detail.get('employee_id')]
        # ID21 = Σ des lignes arrondies par salarié : les totaux de l'imprimé égalent la somme des lignes.
        for box in self._employee_boxes(declaration):
            values[box.code] = sum(row.get(box.code, 0.0) for row in rows)
        values[EMPLOYEES] = len(rows)
        values[ID19_COUNT] = sum(1 for row in rows if row['id19'])
        for tranche, (count_box, total_box) in ID20.items():
            members = [row for row in rows if row['tranche'] == tranche]
            values[count_box] = len(members)
            values[total_box] = sum(row.get(TOTAL_BOX, 0.0) for row in members)
        for box_code in PAYMENT_BOXES.values():
            values[box_code] = sum(d['amount'] for d in details if d.get('box_code') == box_code)
        for box in self._boxes(declaration).filtered(lambda b: b.sum_box_codes and b.section not in ID21_SECTIONS):
            values[box.code] = sum(sign * (values.get(code) or 0.0) for code, sign in box._sum_box_codes())
        codes = {box.code for box in declaration.type_id.box_ids}
        return {code: value for code, value in values.items() if code in codes}

    def _has_official_workbooks(self, declaration):
        return True

    def _official_workbooks(self, declaration):
        books = OfficialWorkbooks(declaration)
        return [('ID19', books.build('ID19', books.id19_rows())), ('ID21', books.build('ID21', books.id21_rows()))]

    def _capacity_issues(self, declaration):
        """Plus de lignes que n'en couvrent les formules du classeur officiel : bouton « Ajouter des lignes »."""
        books = OfficialWorkbooks(declaration)
        issues = []
        for code, rows in (('ID19', books.id19_rows()), ('ID21', books.id21_rows())):
            capacity = OFFICIAL_TEMPLATES[code][2]
            if len(rows) > capacity:
                message = self.env._(
                    '%(code)s : %(count)s lignes pour %(capacity)s préparées dans le classeur officiel ; utilisez '
                    'son bouton « Ajouter des lignes » avant de générer le XML.',
                    code=code,
                    count=len(rows),
                    capacity=capacity,
                )
                issues.append((WARNING, 'GA_DAS_XLSM_CAPACITY', message, declaration))
        return issues

    def _id19_address_issues(self, details):
        """ID19 : BP et ville du salarié obligatoires dans le classeur officiel (avertissement)."""
        issues = []
        for detail in details:
            payload = detail.get('payload') or {}
            if (
                detail.get('employee_id')
                and payload.get('id19')
                and not (payload.get('street') and payload.get('city'))
            ):
                employee = self.env['hr.employee'].browse(detail['employee_id'])
                message = self.env._('%(employee)s : BP ou ville personnelle absente (ID19).', employee=employee.name)
                issues.append((WARNING, 'GA_DAS_ID19_ADDRESS', message, employee))
        return issues

    def _detail_columns(self, declaration):
        env = self.env
        identity = [
            ('registration', env._('Matricule'), 'text'),
            ('number', env._('N° CNSS'), 'text'),
            ('name', env._('Nom et prénoms'), 'text'),
            ('job', env._('Profession'), 'text'),
            ('job_code', env._('Code emploi'), 'text'),
            ('level_code', env._('Code niveau'), 'text'),
            ('nationality', env._('Nat.'), 'text'),
            ('age', env._('Âge'), 'text'),
            ('gender', env._('Sexe'), 'text'),
            ('marital', env._('Sit.'), 'text'),
            ('children', env._('Enf.'), 'text'),
            ('period', env._('Période'), 'text'),
        ]
        return identity + [(box.code, box.name, 'amount') for box in self._employee_boxes(declaration)]

    # --- contrôles --------------------------------------------------------------------------

    def _checks(self, declaration, facts):
        values = self._fill(declaration, facts)
        details = self._details(declaration, facts)
        return (
            super()._checks(declaration, facts)
            + self._reconciliation_issues(declaration, values, facts)
            + self._missing_id10_issues(declaration, facts)
            + self._employee_issues(declaration, details)
            + self._id19_address_issues(details)
            + self._capacity_issues(declaration)
            + self._payment_issues(declaration, values)
            + self._opening_issues(declaration, facts)
        )

    def _reconciliation_issues(self, declaration, values, facts):
        """Total ID21 = Σ des déclarations de l'année (ID10, ID28) pour chaque impôt (base 06 §4).

        Année de bascule (F12) : les mois couverts par les cumuls d'ouverture ont été déclarés hors de
        la V2 ; leurs montants s'ajoutent au déclaré attendu.
        """
        issues = []
        for box in self._boxes(declaration).filtered('control_boxes'):
            refs = box._control_boxes()
            declared = self._year_declarations(declaration, {code for code, _box, _sign in refs})
            expected = sum(
                sign * opening[field] for opening in facts['openings'] for field, sign in box._opening_fields()
            )
            for decl in declared:
                for type_code, box_code, sign in refs:
                    if decl.type_id.code == type_code:
                        line = decl.line_ids.filtered(lambda line, c=box_code: line.code == c)
                        expected += sign * (line.value_amount if line and not line.value_blank else 0.0)
            if float_compare(values.get(box.code) or 0.0, expected, precision_digits=0):
                message = self.env._(
                    '%(box)s : %(das)s dans la DAS, %(declared)s déclarés sur les %(types)s de l’année.',
                    box=box.name,
                    das=values.get(box.code) or 0.0,
                    declared=expected,
                    types=', '.join(sorted({code for code, _box, _sign in refs})),
                )
                issues.append((BLOCKING, 'GA_DAS_ID10', message, declaration))
        return issues

    def _missing_id10_issues(self, declaration, facts):
        declared = {decl.date_from.month for decl in self._year_declarations(declaration, {'ID10'})}
        paid = sorted({slip.l10n_ga_payment_date.month for slip in facts['slips'] if slip.l10n_ga_payment_date})
        return [
            (
                WARNING,
                'GA_DAS_ID10_MISSING',
                self.env._(
                    'Salaires payés en %(month)02d/%(year)s sans ID10.', month=month, year=declaration.date_to.year
                ),
                declaration,
            )
            for month in paid
            if month not in declared
        ]

    def _employee_issues(self, declaration, details):
        issues = []
        for detail in details:
            if not detail.get('employee_id'):
                continue
            employee = self.env['hr.employee'].browse(detail['employee_id'])
            payload = detail['payload']
            if not payload['nif']:
                message = self.env._('%(employee)s : NIF absent (ID21, ID19).', employee=employee.name)
                issues.append((BLOCKING, 'GA_DAS_NO_NIF', message, employee))
            if not (payload['job_code'] and payload['level_code']):
                message = self.env._('%(employee)s : code emploi ou code niveau DGI absent.', employee=employee.name)
                issues.append((WARNING, 'GA_DAS_NO_JOB_CODE', message, employee))
        return issues

    def _payment_issues(self, declaration, values):
        """ID22 : total versé = total des retenues, sinon note explicative (avertissement)."""
        paid = sum(values.get(code) or 0.0 for code in PAYMENT_BOXES.values())
        due = values.get(TAXES_BOX) or 0.0
        if not float_compare(paid, due, precision_digits=0):
            return []
        message = self.env._(
            'ID22 : %(paid)s versés pour %(due)s retenus : joindre une note explicative.', paid=paid, due=due
        )
        return [(WARNING, 'GA_DAS_PAYMENTS', message, declaration)]

    def _opening_issues(self, declaration, facts):
        return [
            (
                WARNING,
                'GA_DAS_OPENING_CFP',
                self.env._(
                    '%(employee)s : cumul d’ouverture sans CFP ni ventilation par colonne (reprise simplifiée).',
                    employee=opening.employee_id.name,
                ),
                opening,
            )
            for opening in facts['openings']
        ]

    # --- classeur ---------------------------------------------------------------------------

    def _render_workbook(self, declaration):
        return DasWorkbook(self, declaration).build()


class DasWorkbook:
    """Classeur DAS lu sur les valeurs figées : ID20, ID21 (39 lignes par feuille), ID22, ID19."""

    def __init__(self, generator, declaration):
        self.env = generator.env
        self.generator = generator
        self.declaration = declaration
        self.values = {line.code: line._value() for line in declaration.line_ids}
        self.names = {line.code: line.box_id.name for line in declaration.line_ids}
        self.rows = [d for d in declaration.detail_ids if d.employee_id]
        self.payments = [d for d in declaration.detail_ids if not d.employee_id]
        self.builder = XlsxDeclarationBuilder()
        self.year = f'{declaration.date_to:%Y}'

    def _identity(self):
        company = self.declaration.company_id
        env = self.env
        return {
            'title': env._('Identification de l’employeur'),
            'pairs': [
                (env._('Raison sociale'), company.name),
                (env._('NIF'), company.l10n_ga_nif or ''),
                (env._('N° employeur CNSS'), company.l10n_ga_cnss_number or ''),
                (env._('Adresse'), ' — '.join(filter(None, [company.street, company.city]))),
                (env._('Exercice'), self.year),
            ],
        }

    def _title(self, code, label):
        return f'{code} — {label} — {self.env._("exercice")} {self.year}'

    def _id20(self):
        env = self.env
        threshold = self.generator._parameter(self.declaration, 'l10n_ga_das_id20_threshold') or 0
        limit = f'{threshold:,.0f}'.replace(',', ' ')
        rows = [
            [
                env._('Inférieure à %(limit)s', limit=limit),
                self.values.get('ID20_B_COUNT'),
                self.values.get('ID20_B_TOTAL'),
            ],
            [
                env._('Égale ou supérieure à %(limit)s', limit=limit),
                self.values.get('ID20_A_COUNT'),
                self.values.get('ID20_A_TOTAL'),
            ],
        ]
        totals = [env._('Total'), sum(r[1] or 0 for r in rows), sum(r[2] or 0 for r in rows)]
        self.builder.form(
            'ID20',
            [
                self._identity(),
                {
                    'title': env._('Rémunérations versées par tranche de salaire mensuel'),
                    'headers': [
                        env._('Tranche de rémunération mensuelle'),
                        env._('Nombre de salariés'),
                        env._('Total des rémunérations'),
                    ],
                    'rows': rows,
                    'totals': totals,
                },
            ],
            title=self._title('ID20', env._('État de la masse salariale')),
            subtitle=self.declaration.name,
        )

    def _pages(self):
        size = int(self.generator._parameter(self.declaration, 'l10n_ga_das_id21_lines') or len(self.rows) or 1)
        return [self.rows[index : index + size] for index in range(0, len(self.rows), size)] or [[]]

    def _id21(self, columns, amount_keys):
        env = self.env
        pages = self._pages()
        for number, page in enumerate(pages, start=1):
            rows = [[self._cell(detail, key) for key, _label, _kind in columns] for detail in page]
            totals = [env._('Total de la feuille')] + [
                sum(row[i] or 0 for row in rows) if columns[i][0] in amount_keys else None
                for i in range(1, len(columns))
            ]
            self.builder.form(
                f'ID21 ({number})',
                [{'headers': [label for _key, label, _kind in columns], 'rows': rows, 'totals': totals}],
                title=self._title('ID21', env._('Bordereau détaillé des salaires')),
                subtitle=env._(
                    '%(name)s — feuille %(page)s / %(pages)s', name=self.declaration.name, page=number, pages=len(pages)
                ),
                landscape=True,
                paper=PAPER_A3,
            )
        return pages

    @staticmethod
    def _cell(detail, key):
        return (detail.payload or {}).get(key)

    def _id22(self, pages, amount_keys):
        env = self.env
        keys = list(amount_keys)
        sheet_rows = [
            [number, len(page), *[sum(self._cell(d, key) or 0 for d in page) for key in keys]]
            for number, page in enumerate(pages, start=1)
        ]
        totals = [
            env._('Total'),
            sum(r[1] for r in sheet_rows),
            *[sum(r[i] for r in sheet_rows) for i in range(2, len(keys) + 2)],
        ]
        kinds = dict(self.env['l10n_ga.declaration.payment']._fields['kind']._description_selection(self.env))
        payment_rows = [
            [
                self._cell(d, 'month'),
                kinds.get(self._cell(d, 'kind'), ''),
                self._cell(d, 'declaration'),
                self._cell(d, 'date') and f'{date.fromisoformat(self._cell(d, "date")):%d/%m/%Y}',
                self._cell(d, 'number'),
                d.amount,
            ]
            for d in self.payments
        ]
        paid = sum(d.amount for d in self.payments)
        due = self.values.get(TAXES_BOX) or 0.0
        blocks = [
            self._identity(),
            {
                'title': env._('Récapitulatif des feuilles de l’ID21'),
                'headers': [env._('Feuille'), env._('Salariés'), *[self.names.get(key, key) for key in keys]],
                'rows': sheet_rows,
                'totals': totals,
            },
            {
                'title': env._('Versements de l’année (quittances)'),
                'headers': [
                    env._('Mois'),
                    env._('Nature'),
                    env._('Déclaration'),
                    env._('Date'),
                    env._('N° de quittance'),
                    env._('Montant'),
                ],
                'rows': payment_rows,
                'totals': [env._('Total versé'), None, None, None, None, paid],
            },
            {
                'title': env._('Contrôle'),
                'headers': [env._('Total versé'), env._('Total des retenues (11)'), env._('Écart')],
                'rows': [[paid, due, paid - due]],
            },
        ]
        if float_compare(paid, due, precision_digits=0):
            blocks.append({'text': env._('Écart entre versements et retenues : joindre une note explicative (ID22).')})
        self.builder.form(
            'ID22',
            blocks,
            title=self._title('ID22', env._('Bordereau récapitulatif')),
            subtitle=self.declaration.name,
            landscape=True,
            paper=PAPER_A3,
        )

    def _id19(self):
        env = self.env
        used = set()
        for detail in self.rows:
            payload = detail.payload or {}
            if not payload.get('id19'):
                continue
            name = f'ID19 {payload.get("name") or ""}'[:SHEET_NAME_MAX]
            while name.lower() in used:  # homonymes : suffixe numéroté, nom de feuille Excel borné
                suffix = f' {len(used)}'
                name = f'{name[: SHEET_NAME_MAX - len(suffix)]}{suffix}'
            used.add(name.lower())

            def amount(code, payload=payload):
                return payload.get(code) or 0.0

            gross = amount(TOTAL_BOX)
            self.builder.form(
                name,
                [
                    self._identity(),
                    {
                        'title': env._('Bénéficiaire'),
                        'pairs': [
                            (env._('Nom et prénoms'), payload.get('name')),
                            (env._('NIF'), payload.get('nif')),
                            (env._('N° CNSS'), payload.get('number')),
                            (env._('Matricule'), payload.get('registration')),
                            (env._('Profession'), payload.get('job')),
                            (
                                env._('Situation familiale / enfants'),
                                f'{payload.get("marital") or ""} / {payload.get("children") or 0}',
                            ),
                            (env._('Période'), payload.get('period')),
                        ],
                    },
                    {
                        'title': env._('Rémunérations de l’année'),
                        'headers': [env._('Désignation'), env._('Montant')],
                        'rows': [
                            *[[self.names.get(code, code), amount(code)] for code in ID19_GAINS],
                            [self.names.get(TOTAL_BOX, TOTAL_BOX), gross],
                            [env._('À déduire : TCS de l’année'), amount('C7')],
                            [env._('Rémunération brute imposable'), gross - amount('C7')],
                            [self.names.get('C8', 'C8'), amount('C8')],
                            *[
                                [self.names.get(code, code), amount(code)]
                                for code in ('NT_HOUSING', 'NT_TRANSPORT', 'NT_DOMESTIC', 'NT_OTHER')
                            ],
                        ],
                        # totaux en gras : total brut, puis rémunération brute imposable
                        'bold': {len(ID19_GAINS), len(ID19_GAINS) + 2},
                    },
                ],
                title=self._title('ID19', env._('Bulletin individuel de justification')),
                subtitle=self.declaration.name,
            )

    def build(self):
        columns = self.generator._detail_columns(self.declaration)
        amount_keys = [key for key, _label, kind in columns if kind == 'amount']
        self._id20()
        pages = self._id21(columns, amount_keys)
        self._id22(pages, amount_keys)
        self._id19()
        return self.builder.build()


class OfficialWorkbooks:
    """ID19 et ID21 : classeurs officiels remplis à partir des détails figés de la DAS (D-87)."""

    def __init__(self, declaration):
        self.declaration = declaration
        self.rows = declaration._l10n_ga_details(employees=True)
        self.header_values = (
            declaration.company_id.l10n_ga_nif or '',
            declaration.date_to.year,
            ANNUAL,
        )

    @staticmethod
    def _date(value):
        return date.fromisoformat(value) if value else None

    def _rate(self, code):
        return self.declaration._l10n_ga_parameter(code) or 0.0

    def id21_rows(self):
        return [
            {
                'B': row.get('nif'),
                'C': row.get('name'),
                'D': row.get('job_code'),
                'E': row.get('level_code'),
                'F': ID21_NATIONALITY.get(str(row.get('nationality') or '')),
                'G': row.get('age') if row.get('age') != '' else None,
                'H': ID21_GENDER.get(str(row.get('gender') or '')),
                'I': ID21_MARITAL.get(str(row.get('marital') or '')),
                'J': row.get('children') or 0,
                'K': self._date(row.get('date_start')),
                'L': self._date(row.get('date_end')),
                'M': row.get('C1') or 0,
                'N': row.get('C2') or 0,
                'O': row.get('C3') or 0,
                'P': row.get('C5') or 0,
                'Q': row.get('C4') or 0,
                'S': row.get('C7') or 0,
                'T': row.get('C8') or 0,
                'U': row.get('C10') or 0,
                'W': row.get('NT_TOTAL') or 0,
            }
            for row in self.rows
        ]

    def _id19_amounts(self, row):
        """``[(nature, montant de la colonne V)]`` d'un salarié : pour un avantage en nature, V est la base
        dont le classeur tire l'avantage (colonne AG = V × taux) ; ailleurs V est le montant (taux 100 %)."""
        amounts = [('presence', (row.get('C1') or 0) + (row.get('C4') or 0)), ('leave', row.get('C5') or 0)]
        benefits = [(kind, row.get(key) or 0, rate) for kind, key, _codes, rate in AIK_KINDS]
        benefits.append(('food', row.get(FOOD_BOX) or 0, FOOD_RATE))
        for kind, amount, rate_code in benefits:
            rate = self._rate(rate_code)
            if amount and rate:
                amounts.append((kind, float_round(amount / rate, precision_digits=0)))
        amounts += [('tcs', row.get('C7') or 0), ('irpp', row.get('C8') or 0), ('exempt', row.get('NT_TOTAL') or 0)]
        return [(kind, value) for kind, value in amounts if value or kind == 'presence']

    def id19_rows(self):
        lines = []
        for row in (r for r in self.rows if r.get('id19')):
            identity = {
                'B': row.get('nif'),
                'C': row.get('name'),
                'D': row.get('job'),
                'E': row.get('phone'),
                'F': row.get('street'),
                'G': row.get('city'),
                'H': ID19_MARITAL.get(str(row.get('marital') or ''), ID19_MARITAL_UNKNOWN),
                'I': row.get('children') or 0,
                'J': self._date(row.get('date_start')),
                'K': self._date(row.get('date_end')),
            }
            lines += [{**identity, 'T': ID19_NATURES[kind], 'V': value} for kind, value in self._id19_amounts(row)]
        return lines

    def build(self, code, rows):
        path, first_row, _capacity = OFFICIAL_TEMPLATES[code]
        with file_open(path, 'rb') as template:
            workbook = SaisieWorkbook(template.read())
        header = dict(zip(HEADER_CELLS, self.header_values, strict=True))
        return workbook.fill(header, first_row, rows).build()
