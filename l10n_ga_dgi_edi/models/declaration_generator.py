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

    def _payslip_domain(self, declaration):
        date_field = 'l10n_ga_payment_date' if declaration.type_id.period_basis == 'payment_date' else 'date_to'
        return [
            ('slip_id.company_id', '=', declaration.company_id.id),
            ('slip_id.state', 'in', VALIDATED_STATES),
            (f'slip_id.{date_field}', '>=', declaration.date_from),
            (f'slip_id.{date_field}', '<=', declaration.date_to),
        ]

    def _collect(self, declaration):
        """Lignes agrégées par (salarié, rubrique) : code, catégorie, montant, base, part exclue, lignes."""
        boxes = self._boxes(declaration)
        codes = sorted({code for box in boxes for code, _sign in box._source_codes()})
        categories = sorted({code for box in boxes for code, _sign in box._source_categories()})
        if not (codes or categories):
            return []
        groups = self.env['hr.payslip.line']._read_group(
            [
                *self._payslip_domain(declaration),
                '|',
                ('code', 'in', codes),
                ('salary_rule_id.category_id.code', 'in', categories),
            ],
            ['employee_id', 'salary_rule_id'],
            ['total:sum', 'l10n_ga_base:sum', 'l10n_ga_social_excluded:sum', 'id:recordset'],
        )
        return [
            {
                'employee': employee,
                'code': rule.code,
                'category': rule.category_id.code,
                'total': total,
                'base': base,
                'social_excluded': excluded,
                'lines': lines,
            }
            for employee, rule, total, base, excluded, lines in groups
        ]

    def _measure(self, declaration, fact, measure):
        if measure == 'base':
            return fact['base']
        if measure == 'cfp' and declaration.company_id.l10n_ga_cfp_base != 'gross':
            return fact['total'] - fact['social_excluded']
        return fact['total']

    def _sign(self, box, fact):
        """Signe de la ligne pour la case, ou 0 si elle n'y entre pas (le code prime sur la catégorie)."""
        codes = dict(box._source_codes())
        if fact['code'] in codes:
            return codes[fact['code']]
        return dict(box._source_categories()).get(fact['category'], 0)

    def _contributions(self, declaration, facts):
        """``{case: {salarié: [montant, lignes]}}`` pour les cases alimentées par les bulletins."""
        result = {}
        for box in self._boxes(declaration).filtered(lambda b: b._has_source()):
            per_employee = result.setdefault(box.code, {})
            for fact in facts:
                sign = self._sign(box, fact)
                if sign:
                    entry = per_employee.setdefault(fact['employee'], [0.0, self.env['hr.payslip.line']])
                    entry[0] += sign * self._measure(declaration, fact, box.source_measure)
                    entry[1] |= fact['lines']
        return result

    def _fill(self, declaration, facts):
        values = {
            code: sum(amount for amount, _lines in per_employee.values())
            for code, per_employee in self._contributions(declaration, facts).items()
        }
        Parameter = self.env['hr.rule.parameter'].sudo()
        boxes = self._boxes(declaration)
        for box in boxes.filtered('parameter_code'):
            values[box.code] = Parameter._get_parameter_from_code(
                box.parameter_code, declaration.date_to, raise_if_not_found=False
            )
        for box in boxes.filtered('sum_box_codes'):  # dans l'ordre des cases : une somme peut en reprendre une autre
            values[box.code] = sum(sign * (values.get(code) or 0.0) for code, sign in box._sum_box_codes())
        return values

    def _details(self, declaration, facts):
        details = []
        for box_code, per_employee in self._contributions(declaration, facts).items():
            for employee, (amount, lines) in sorted(per_employee.items(), key=lambda i: (i[0].name or '', i[0].id)):
                details.append(
                    {
                        'box_code': box_code,
                        'employee_id': employee.id,
                        'label': employee.name,
                        'amount': amount,
                        'payslip_line_ids': lines.ids,
                    }
                )
        return details

    def _required_parameters(self, declaration):
        return sorted(set(self._boxes(declaration).filtered('parameter_code').mapped('parameter_code')))
