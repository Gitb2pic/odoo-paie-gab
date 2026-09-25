"""Contrôles communs des déclarations (patron 8 « Chain of Responsibility », RG15, ADR-18).

Chaque contrôle est indépendant : ``run(declaration, facts)`` renvoie ses anomalies
``(gravité, code, message, enregistrement)``. La déclaration enchaîne ces contrôles puis ceux du
générateur ; une anomalie bloquante empêche la validation.
"""

from odoo.addons.l10n_ga_hr_payroll.models.l10n_ga_payroll_check import BLOCKING, CheckRule
from odoo.tools import float_compare


class DeclarationCheckRule(CheckRule):
    """Même contrat que les contrôles de paie, appliqué à une déclaration."""

    def applies(self, declaration):
        return True

    def run(self, declaration, facts=None):  # pylint: disable=arguments-differ
        raise NotImplementedError  # interface abstraite (patron 8)


class MissingCnssNumber(DeclarationCheckRule):
    """Salarié déclaré sans n° CNSS : avertissement en paie, bloquant en déclaration (D-71)."""

    code = 'GA_DECL_NO_CNSS'

    def applies(self, declaration):
        return declaration._generator()._requires_cnss_number(declaration)

    def run(self, declaration, facts=None):
        employees = declaration.detail_ids.employee_id.filtered(lambda e: not e.ssnid)
        return [
            self.issue(declaration.env._('%(employee)s : n° CNSS absent.', employee=employee.name), employee)
            for employee in employees.sorted('name')
        ]


class DuplicatePeriod(DeclarationCheckRule):
    """Autre déclaration active du même type dont la période chevauche celle-ci (RG11)."""

    code = 'GA_DECL_DUPLICATE'

    def applies(self, declaration):
        return not declaration.rectified_id

    def run(self, declaration, facts=None):
        others = declaration.search(
            [
                ('id', '!=', declaration.id),
                ('company_id', '=', declaration.company_id.id),
                ('type_id', '=', declaration.type_id.id),
                ('rectified_id', '=', False),
                ('state', '!=', 'cancel'),
                ('date_from', '<=', declaration.date_to),
                ('date_to', '>=', declaration.date_from),
            ]
        )
        return [
            self.issue(declaration.env._('Période déjà couverte par la déclaration %(name)s.', name=other.name), other)
            for other in others
        ]


class ParameterMissing(DeclarationCheckRule):
    """Paramètre daté requis par le générateur sans valeur à la fin de période (règle d'or 1)."""

    code = 'GA_DECL_PARAM_MISSING'

    def run(self, declaration, facts=None):
        generator = declaration._generator()
        Parameter = declaration.env['hr.rule.parameter'].sudo()
        issues = []
        for code in generator._required_parameters(declaration):
            value = Parameter._get_parameter_from_code(code, declaration.date_to, raise_if_not_found=False)
            if value is None:
                message = declaration.env._(
                    'Paramètre « %(code)s » sans valeur au %(date)s.', code=code, date=declaration.date_to
                )
                issues.append(self.issue(message, declaration))
        return issues


class TotalsMatchDetails(DeclarationCheckRule):
    """Chaque case justifiée par des détails doit égaler la somme de ses détails (RG13)."""

    code = 'GA_DECL_TOTALS'

    def run(self, declaration, facts=None):
        currency = declaration.currency_id
        issues = []
        for line in declaration.line_ids.filtered(lambda line: line.box_id.value_kind == 'amount'):
            details = declaration.detail_ids.filtered(lambda d, box=line.box_id: d.box_id == box)
            if not details:
                continue
            total = sum(details.mapped('amount'))
            if float_compare(total, line.value_amount, precision_rounding=currency.rounding):
                message = declaration.env._(
                    'Case %(box)s : %(value)s déclaré, %(total)s dans le détail.',
                    box=line.box_id.code,
                    value=line.value_amount,
                    total=total,
                )
                issues.append(self.issue(message, declaration))
        return issues


COMMON_CHECKS = (MissingCnssNumber(), DuplicatePeriod(), ParameterMissing(), TotalsMatchDetails())


def run_checks(declaration, facts, checks=COMMON_CHECKS):
    """Enchaîne les contrôles applicables à la déclaration."""
    issues = []
    for check in checks:
        if check.applies(declaration):
            issues += check.run(declaration, facts)
    return issues


__all__ = ['BLOCKING', 'COMMON_CHECKS', 'run_checks']
