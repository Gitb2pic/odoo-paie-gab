"""Registre des générateurs d'imprimés et interface Strategy (patrons 4 et 5, ADR-07).

Un générateur est un modèle abstrait ``l10n_ga.declaration.generator.<clé>`` qui hérite de
``l10n_ga.declaration.generator.base``. Le type de déclaration (donnée) porte la clé ; le moteur
(``l10n_ga.declaration.action_compute``) ne connaît que l'interface.
"""

from odoo import models

BLOCKING = 'blocking'
WARNING = 'warning'
VALIDATED_STATES = ('validated', 'paid')  # sprint 0 point 3 : plus d'état « done » en 19
GENERATOR_PREFIX = 'l10n_ga.declaration.generator.'


class L10nGaDeclarationGenerator(models.AbstractModel):
    _name = 'l10n_ga.declaration.generator'
    _description = 'Registre des générateurs de déclarations (Gabon)'

    def _model_name(self, key):
        return GENERATOR_PREFIX + (key or '').strip().lower()

    def _has(self, key):
        return bool(key) and self._model_name(key) in self.env and key.strip().lower() != 'base'

    def _get(self, key):
        if not self._has(key):
            raise KeyError(key)
        return self.env[self._model_name(key)]


class L10nGaDeclarationGeneratorBase(models.AbstractModel):
    """Interface d'une stratégie de collecte : étapes variables du Template Method."""

    _name = 'l10n_ga.declaration.generator.base'
    _description = 'Générateur de déclaration (interface)'

    def _collect(self, declaration):
        """Faits de la période (structure libre, passée aux étapes suivantes)."""
        raise NotImplementedError  # interface abstraite (patron 4)

    def _fill(self, declaration, facts):
        """Valeurs des cases : ``{code de case: valeur}``."""
        raise NotImplementedError  # interface abstraite (patron 4)

    def _details(self, declaration, facts):
        """Lignes de détail : dictionnaires ``box_code``, ``employee_id``, ``partner_id``, ``label``,
        ``amount``, ``payload``, ``payslip_line_ids``."""
        return []

    def _checks(self, declaration, facts):
        """Anomalies propres à l'imprimé : ``(gravité, code, message, enregistrement)``."""
        return []

    def _required_parameters(self, declaration):
        """Codes ``hr.rule.parameter`` qui doivent avoir une valeur à la fin de période."""
        return []

    def _applies(self, company):
        """L'imprimé concerne-t-il la société ? Sinon ni l'Observer ni le cron ne le préparent."""
        return True

    def _requires_cnss_number(self, declaration):
        """Le contrôle commun « n° CNSS manquant » s'applique-t-il à cet imprimé ?"""
        return True

    def _render_workbook(self, declaration):
        """Classeur propre à l'imprimé (DAS : ID20, ID21 paginé, ID22, ID19), ou ``None`` = classeur standard."""
        return None

    def _detail_columns(self, declaration):
        """Colonnes du détail nominatif ``[(clé du payload, libellé, nature)]`` (nature : amount, text,
        date) ; vide = détail par case."""
        return []


class L10nGaDeclarationGeneratorPayslip(models.AbstractModel):
    """Générateur générique piloté par les cases (codes de rubriques et catégories en données, prompt 04).

    Lit les lignes des bulletins **validés ou payés** de la société, rattachés à la période par la
    date de paiement (ou la date de fin selon le type). Une case vaut, au choix :
    la somme signée de rubriques / catégories (mesure : montant, base figée ou part CFP) ;
    un paramètre daté ; la somme d'autres cases. Les imprimés de paie (ID10, ID28, DTS) en héritent.
    """

    _name = 'l10n_ga.declaration.generator.payslip'
    _inherit = 'l10n_ga.declaration.generator.base'
    _description = 'Générateur générique : rubriques de paie'

    # --- points d'extension des imprimés ---------------------------------------------------------

    def _blank_sections(self, declaration):
        """Cadres laissés vides (cases non renseignées) pour cette déclaration."""
        return set()

    def _boxes(self, declaration):
        blank = self._blank_sections(declaration)
        return declaration.type_id.box_ids.filtered(lambda box: not box.section or box.section not in blank)

    # --- collecte --------------------------------------------------------------------------------

    def _date_field(self, declaration):
        return 'l10n_ga_payment_date' if declaration.type_id.period_basis == 'payment_date' else 'date_to'

    def _payslip_domain(self, declaration, prefix='slip_id.'):
        date_field = self._date_field(declaration)
        return [
            (f'{prefix}company_id', '=', declaration.company_id.id),
            (f'{prefix}state', 'in', VALIDATED_STATES),
            (f'{prefix}{date_field}', '>=', declaration.date_from),
            (f'{prefix}{date_field}', '<=', declaration.date_to),
        ]

    @staticmethod
    def _month_of(declaration, day):
        """Rang du mois de ``day`` dans la période (0 = premier mois)."""
        return (day.year - declaration.date_from.year) * 12 + day.month - declaration.date_from.month

    def _month_index(self, declaration, slip):
        return self._month_of(declaration, slip[self._date_field(declaration)])

    def _month_count(self, declaration):
        return self._month_of(declaration, declaration.date_to) + 1

    def _collect(self, declaration):
        """Bulletins de la période et leurs lignes agrégées par (bulletin, rubrique)."""
        boxes = self._boxes(declaration)
        codes = sorted({code for box in boxes for code, _sign in box._source_codes()})
        categories = sorted({code for box in boxes for code, _sign in box._source_categories()})
        das_columns = sorted(set(boxes.mapped('source_das_column')) - {False})
        slips = self.env['hr.payslip'].search(self._payslip_domain(declaration, prefix=''))
        facts = {'slips': slips, 'lines': []}
        if not (codes or categories or das_columns):
            return facts
        groups = self.env['hr.payslip.line']._read_group(
            [
                ('slip_id', 'in', slips.ids),
                '|',
                '|',
                '|',
                ('code', 'in', codes),
                ('salary_rule_id.category_id.code', 'in', categories),
                ('salary_rule_id.l10n_ga_das_column', 'in', das_columns),
                ('salary_rule_id.l10n_ga_das_exempt_column', 'in', das_columns),
            ],
            ['slip_id', 'salary_rule_id'],
            [
                'total:sum',
                'l10n_ga_base:sum',
                'l10n_ga_social_excluded:sum',
                'l10n_ga_tax_exempt:sum',
                'id:recordset',
            ],
        )
        facts['lines'] = [
            {
                'employee': slip.employee_id,
                'slip': slip,
                'month': self._month_index(declaration, slip),
                'code': rule.code,
                'category': rule.category_id.code,
                'total': total,
                'base': base,
                'social_excluded': excluded,
                'tax_exempt': exempt,
                'das_column': rule.l10n_ga_das_column,
                'das_exempt_column': rule.l10n_ga_das_exempt_column,
                'lines': lines,
            }
            for slip, rule, total, base, excluded, exempt, lines in groups
        ]
        return facts

    def _measure(self, declaration, fact, measure):
        if measure == 'base':
            return fact['base']
        if measure == 'social' or (measure == 'cfp' and declaration.company_id.l10n_ga_cfp_base != 'gross'):
            return fact['total'] - fact['social_excluded']
        return fact['total']

    def _sign(self, box, fact, declaration=None):
        """Signe de la ligne pour la case, ou 0 si elle n'y entre pas (le code prime sur la catégorie)."""
        codes = dict(box._source_codes())
        if fact['code'] in codes:
            return codes[fact['code']]
        return dict(box._source_categories()).get(fact['category'], 0)

    @staticmethod
    def _das_value(box, fact):
        """Part de la ligne classée dans la colonne DAS de la case (imposable et / ou exonérée, F16)."""
        column = box.source_das_column
        if not column:
            return 0.0
        value = 0.0
        if fact['das_column'] == column:
            value += fact['total'] - fact['tax_exempt']
        if fact['das_exempt_column'] == column:
            value += fact['tax_exempt']
        return value

    def _contributions(self, declaration, facts):
        """``{case: {salarié: {'amount', 'lines', 'months'}}}`` pour les cases alimentées par les bulletins."""
        months = self._month_count(declaration)
        result = {}

        def entry(per_employee, employee):
            return per_employee.setdefault(
                employee, {'amount': 0.0, 'lines': self.env['hr.payslip.line'], 'months': [0.0] * months}
            )

        for box in self._boxes(declaration).filtered(lambda b: b._has_source()):
            per_employee = result.setdefault(box.code, {})
            for fact in facts['lines']:
                sign = self._sign(box, fact, declaration)
                das = self._das_value(box, fact)
                if sign or das:
                    value = sign * self._measure(declaration, fact, box.source_measure) + das
                    item = entry(per_employee, fact['employee'])
                    item['amount'] += value
                    item['months'][fact['month']] += value
                    item['lines'] |= fact['lines']
            if box.source_slip_field:
                for slip in facts['slips']:
                    item = entry(per_employee, slip.employee_id)
                    item['amount'] += slip[box.source_slip_field]
                    item['months'][self._month_index(declaration, slip)] += slip[box.source_slip_field]
        return result

    def _fill(self, declaration, facts):
        boxes = self._boxes(declaration)
        measures = dict(boxes.mapped(lambda b: (b.code, b.source_measure)))
        values = {
            code: len(per_employee)
            if measures[code] == 'count'
            else sum(item['amount'] for item in per_employee.values())
            for code, per_employee in self._contributions(declaration, facts).items()
        }
        Parameter = self.env['hr.rule.parameter'].sudo()
        for box in boxes.filtered('parameter_code'):
            values[box.code] = Parameter._get_parameter_from_code(
                box.parameter_code, declaration.date_to, raise_if_not_found=False
            )
        for box in boxes.filtered('sum_box_codes'):  # dans l'ordre des cases : une somme peut en reprendre une autre
            values[box.code] = sum(sign * (values.get(code) or 0.0) for code, sign in box._sum_box_codes())
        return values

    def _details(self, declaration, facts):
        """Détail par case et par salarié (hors cases de comptage)."""
        counted = set(self._boxes(declaration).filtered(lambda b: b.source_measure == 'count').mapped('code'))
        details = []
        for box_code, per_employee in self._contributions(declaration, facts).items():
            if box_code in counted:
                continue
            for employee, item in sorted(per_employee.items(), key=lambda i: (i[0].name or '', i[0].id)):
                details.append(
                    {
                        'box_code': box_code,
                        'employee_id': employee.id,
                        'label': employee.name,
                        'amount': item['amount'],
                        'payslip_line_ids': item['lines'].ids,
                    }
                )
        return details

    def _required_parameters(self, declaration):
        boxes = self._boxes(declaration)
        return sorted(set(boxes.mapped('parameter_code') + boxes.mapped('ceiling_parameter')) - {False})
