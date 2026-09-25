from calendar import monthrange

from dateutil.relativedelta import relativedelta

from odoo import models
from odoo.tools import float_compare, float_round

from ..declaration_generator import BLOCKING, WARNING


class L10nGaDeclarationGeneratorDtsCnss(models.AbstractModel):
    """DTS CNSS trimestrielle (base 03 §3 et §5) : état nominatif, salaires des 3 mois, cotisations.

    Cases et rubriques en données ; ce générateur ajoute le détail nominatif (une ligne par salarié,
    colonnes mensuelles des cases « mensuelles ») et les contrôles propres aux DTS.
    """

    _name = 'l10n_ga.declaration.generator.dts_cnss'
    _inherit = 'l10n_ga.declaration.generator.payslip'
    _description = 'DTS CNSS — déclaration trimestrielle des salaires'

    _number_field = 'l10n_ga_ssnid'  # n° figé sur le bulletin validé
    _version_number_field = 'ssnid'  # à défaut, n° de la version du jour (correction après validation)

    def _number_label(self):
        return self.env._('N° CNSS')

    def _nominative_boxes(self, declaration):
        return self._boxes(declaration).filtered(lambda b: b._has_source() and b.source_measure != 'count')

    def _month_labels(self, declaration):
        return [
            f'{declaration.date_from + relativedelta(months=index):%m/%Y}'
            for index in range(self._month_count(declaration))
        ]

    def _employee_number(self, slips):
        for slip in slips.sorted('date_to', reverse=True):
            if slip[self._number_field]:
                return slip[self._number_field]
        return slips[-1:].employee_id.version_id[self._version_number_field] or ''

    def _details(self, declaration, facts):
        contributions = self._contributions(declaration, facts)
        boxes = self._nominative_boxes(declaration)
        total_codes = boxes.filtered('is_total').mapped('code')
        employees = {employee for per_employee in contributions.values() for employee in per_employee}
        details = []
        for employee in sorted(employees, key=lambda e: (e.name or '', e.id)):
            slips = facts['slips'].filtered(lambda s, e=employee: s.employee_id == e).sorted('date_to')
            version = slips[-1:].version_id
            departure = version.departure_date or version.contract_date_end
            payload = {
                'number': self._employee_number(slips),
                'name': slips[-1:].l10n_ga_employee_name or employee.name,
                'hire_date': str(slips[-1:].l10n_ga_hire_date or version.contract_date_start or ''),
                'departure_date': str(departure) if departure and departure <= declaration.date_to else '',
            }
            lines = self.env['hr.payslip.line']
            for box in boxes:
                item = contributions[box.code].get(employee)
                payload[box.code] = float_round(item['amount'] if item else 0.0, precision_digits=0)
                if box.monthly:
                    for index, amount in enumerate(item['months'] if item else [0.0] * self._month_count(declaration)):
                        payload[f'{box.code}_m{index + 1}'] = float_round(amount, precision_digits=0)
                if item:
                    lines |= item['lines']
            details.append(
                {
                    'employee_id': employee.id,
                    'label': payload['name'],
                    'amount': sum(payload[code] for code in total_codes),
                    'payload': payload,
                    'payslip_line_ids': lines.ids,
                }
            )
        return details

    def _detail_columns(self, declaration):
        env = self.env
        columns = [
            ('number', self._number_label(), 'text'),
            ('name', env._('Nom et prénoms'), 'text'),
            ('hire_date', env._('Date d’entrée'), 'date'),
            ('departure_date', env._('Date de sortie'), 'date'),
        ]
        months = self._month_labels(declaration)
        for box in self._nominative_boxes(declaration):
            if box.monthly:
                columns += [
                    (f'{box.code}_m{index + 1}', f'{box.name} {label}', 'amount') for index, label in enumerate(months)
                ]
            columns.append((box.code, box.name, 'amount'))
        return columns

    def _checks(self, declaration, facts):
        return (
            super()._checks(declaration, facts)
            + self._ceiling_issues(declaration, facts)
            + self._total_issues(declaration, facts)
        )

    def _ceiling_issues(self, declaration, facts):
        """Plafond mensuel dépassé par la somme de plusieurs bulletins d'un même mois (avertissement)."""
        Parameter = self.env['hr.rule.parameter'].sudo()
        contributions = self._contributions(declaration, facts)
        issues = []
        for box in self._boxes(declaration).filtered(lambda b: b.monthly and b.ceiling_parameter):
            for index in range(self._month_count(declaration)):
                month_start = declaration.date_from + relativedelta(months=index)
                month_end = month_start.replace(day=monthrange(month_start.year, month_start.month)[1])
                ceiling = Parameter._get_parameter_from_code(box.ceiling_parameter, month_end, raise_if_not_found=False)
                if ceiling is None:
                    continue  # signalé par le contrôle commun « paramètre manquant »
                for employee, item in contributions.get(box.code, {}).items():
                    if float_compare(item['months'][index], ceiling, precision_digits=0) > 0:
                        message = self.env._(
                            '%(employee)s : %(box)s de %(month)s = %(amount)s, au-delà du plafond %(ceiling)s '
                            '(plusieurs bulletins dans le mois).',
                            employee=employee.name,
                            box=box.name,
                            month=f'{month_start:%m/%Y}',
                            amount=item['months'][index],
                            ceiling=ceiling,
                        )
                        issues.append((WARNING, 'GA_DTS_CEILING', message, employee))
        return issues

    def _total_issues(self, declaration, facts):
        """Σ des lignes nominatives = total dû de la déclaration (bloquant)."""
        values = self._fill(declaration, facts)
        due = sum(
            float_round(values.get(box.code) or 0.0, precision_digits=0)
            for box in self._boxes(declaration).filtered('is_total')
        )
        listed = sum(detail['amount'] for detail in self._details(declaration, facts))
        if not float_compare(due, listed, precision_digits=0):
            return []
        message = self.env._('Total des salariés %(listed)s différent du total dû %(due)s.', listed=listed, due=due)
        return [(BLOCKING, 'GA_DTS_TOTALS', message, declaration)]


class L10nGaDeclarationGeneratorDtsCnamgs(models.AbstractModel):
    """DTS CNAMGS trimestrielle : même détail nominatif, n° CNAMGS au lieu du n° CNSS (D-86)."""

    _name = 'l10n_ga.declaration.generator.dts_cnamgs'
    _inherit = 'l10n_ga.declaration.generator.dts_cnss'
    _description = 'DTS CNAMGS — déclaration trimestrielle des salaires'

    _number_field = 'l10n_ga_cnamgs_number'
    _version_number_field = 'l10n_ga_cnamgs_number'

    def _number_label(self):
        return self.env._('N° CNAMGS')

    def _requires_cnss_number(self, declaration):
        return False

    def _checks(self, declaration, facts):
        issues = super()._checks(declaration, facts)
        employees = self.env['hr.employee'].browse(
            detail['employee_id'] for detail in self._details(declaration, facts) if not detail['payload']['number']
        )
        return issues + [
            (BLOCKING, 'GA_DECL_NO_CNAMGS', self.env._('%(employee)s : n° CNAMGS absent.', employee=e.name), e)
            for e in employees
        ]
