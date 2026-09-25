"""Registre des générateurs d'imprimés et interface Strategy (patrons 4 et 5, ADR-07).

Un générateur est un modèle abstrait ``l10n_ga.declaration.generator.<clé>`` qui hérite de
``l10n_ga.declaration.generator.base``. Le type de déclaration (donnée) porte la clé ; le moteur
(``l10n_ga.declaration.action_compute``) ne connaît que l'interface.
"""

from collections import defaultdict

from odoo import models

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


class L10nGaDeclarationGeneratorPayslip(models.AbstractModel):
    """Générateur générique : chaque case = Σ des rubriques de paie listées sur la case (``source_codes``).

    Lit les lignes des bulletins **validés ou payés** de la société, rattachés à la période par la
    date de paiement (ou la date de fin selon le type). Les codes de rubriques viennent des données
    (cases), jamais du code (prompt 04). Les imprimés de paie (ID10, ID28, DTS) en héritent.
    """

    _name = 'l10n_ga.declaration.generator.payslip'
    _inherit = 'l10n_ga.declaration.generator.base'
    _description = 'Générateur générique : somme de rubriques de paie'

    def _payslip_domain(self, declaration):
        date_field = 'l10n_ga_payment_date' if declaration.type_id.period_basis == 'payment_date' else 'date_to'
        return [
            ('slip_id.company_id', '=', declaration.company_id.id),
            ('slip_id.state', 'in', VALIDATED_STATES),
            (f'slip_id.{date_field}', '>=', declaration.date_from),
            (f'slip_id.{date_field}', '<=', declaration.date_to),
        ]

    def _box_codes(self, declaration):
        return {box.code: box._source_codes() for box in declaration.type_id.box_ids if box._source_codes()}

    def _box_signs(self, declaration):
        return {box.code: -1 if box.negate else 1 for box in declaration.type_id.box_ids}

    def _collect(self, declaration):
        """``{(salarié, code de rubrique): (total, lignes)}``."""
        codes = sorted({code for box_codes in self._box_codes(declaration).values() for code in box_codes})
        if not codes:
            return {}
        groups = self.env['hr.payslip.line']._read_group(
            [*self._payslip_domain(declaration), ('code', 'in', codes)],
            ['employee_id', 'code'],
            ['total:sum', 'id:recordset'],
        )
        return {(employee, code): (total, lines) for employee, code, total, lines in groups}

    def _fill(self, declaration, facts):
        signs = self._box_signs(declaration)
        return {
            box_code: signs[box_code]
            * sum(total for (_employee, code), (total, _lines) in facts.items() if code in codes)
            for box_code, codes in self._box_codes(declaration).items()
        }

    def _details(self, declaration, facts):
        signs = self._box_signs(declaration)
        per_box = defaultdict(lambda: [0.0, self.env['hr.payslip.line']])
        for box_code, codes in self._box_codes(declaration).items():
            for (employee, code), (total, lines) in facts.items():
                if code in codes:
                    entry = per_box[box_code, employee]
                    entry[0] += signs[box_code] * total
                    entry[1] |= lines
        return [
            {
                'box_code': box_code,
                'employee_id': employee.id,
                'label': employee.name,
                'amount': amount,
                'payslip_line_ids': lines.ids,
            }
            for (box_code, employee), (amount, lines) in sorted(
                per_box.items(), key=lambda item: (item[0][0], item[0][1].name or '', item[0][1].id)
            )
        ]
