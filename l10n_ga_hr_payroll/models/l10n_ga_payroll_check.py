"""Contrôles avant paie (F8, patron 8 « Chain of Responsibility », D-39).

Chaque contrôle est indépendant : ``run(slip)`` renvoie ses anomalies (gravité, code, message,
enregistrement à corriger). ``PAYROLL_CHECKS`` s'exécute sur les bulletins brouillons d'un lot
avant calcul ; ``l10n_ga_dgi_edi`` réutilisera les contrôles salarié pour les déclarations (ADR-18).
Les données indispensables au calcul bloquent ; celles qui servent au paiement ou aux
déclarations avertissent (elles bloquent dans les déclarations, étape 4).
"""

from ..lib.ga_fiscal_core.loans import LoanFacts, MaxInstallmentRatio
from ..lib.ga_fiscal_core.parts import MARITAL_CODES

BLOCKING = 'blocking'
WARNING = 'warning'
VALIDATED_STATES = ('validated', 'paid')


class CheckRule:
    code = None
    severity = BLOCKING

    def applies(self, slip):
        return bool(slip.version_id)

    def run(self, slip):
        """Liste de ``(gravité, code, message, enregistrement)``."""
        raise NotImplementedError  # interface abstraite du patron 8

    def issue(self, message, record):
        return (self.severity, self.code, message, record)


class NoVersionOnPeriod(CheckRule):
    code = 'GA_NO_VERSION'

    def applies(self, slip):
        return True

    def run(self, slip):
        version = slip.version_id
        valid = (
            version
            and version.date_version <= slip.date_to
            and (not version.contract_date_start or version.contract_date_start <= slip.date_to)
            and (not version.contract_date_end or version.contract_date_end >= slip.date_from)
        )
        if valid:
            return []
        message = slip.env._(
            '%(employee)s : aucune version du contrat valide du %(start)s au %(end)s.',
            employee=slip.employee_id.name,
            start=slip.date_from,
            end=slip.date_to,
        )
        return [self.issue(message, slip.employee_id)]


class MissingHireDate(CheckRule):
    code = 'GA_NO_HIRE_DATE'

    def run(self, slip):
        if slip.version_id.contract_date_start:
            return []
        message = slip.env._('%(employee)s : date d’embauche absente.', employee=slip.employee_id.name)
        return [self.issue(message, slip.version_id)]


class MissingMarital(CheckRule):
    """Situation absente ou inconnue du quotient familial (valeur ajoutée par un autre module)."""

    code = 'GA_NO_MARITAL'

    def run(self, slip):
        if slip.version_id.marital in MARITAL_CODES:
            return []
        message = slip.env._(
            '%(employee)s : situation familiale absente ou non prise en charge par le quotient familial.',
            employee=slip.employee_id.name,
        )
        return [self.issue(message, slip.version_id)]


class ForcedPartsWithoutReason(CheckRule):
    code = 'GA_FORCED_PARTS_NO_REASON'

    def run(self, slip):
        version = slip.version_id
        if not version.l10n_ga_tax_parts_forced or (version.l10n_ga_tax_parts_forced_reason or '').strip():
            return []
        message = slip.env._('%(employee)s : parts fiscales forcées sans motif.', employee=slip.employee_id.name)
        return [self.issue(message, version)]


class WageBelowGradeMinimum(CheckRule):
    code = 'GA_BELOW_GRADE'

    def applies(self, slip):
        return bool(slip.version_id.l10n_ga_grade_id)

    def run(self, slip):
        version = slip.version_id
        minimum = version._l10n_ga_grade_minimum(slip.date_to)
        if version.wage >= minimum:
            return []
        message = slip.env._(
            '%(employee)s : salaire %(wage)s inférieur au minimum %(minimum)s de la grille au %(date)s.',
            employee=slip.employee_id.name,
            wage=version.wage,
            minimum=minimum,
            date=slip.date_to,
        )
        return [self.issue(message, version)]


class AllowanceForcedWithoutReason(CheckRule):
    code = 'GA_ALLOWANCE_FORCED_NO_REASON'

    def run(self, slip):
        allowances = slip._l10n_ga_valid_allowances().filtered(
            lambda a: a.l10n_ga_forced_taxable and not (a.l10n_ga_forced_reason or '').strip()
        )
        return [
            self.issue(
                slip.env._(
                    '%(employee)s : indemnité « %(allowance)s » forcée imposable sans motif.',
                    employee=slip.employee_id.name,
                    allowance=allowance.description or allowance.other_input_type_id.name,
                ),
                allowance,
            )
            for allowance in allowances
        ]


class MissingCnssNumber(CheckRule):
    code = 'GA_NO_CNSS'
    severity = WARNING

    def run(self, slip):
        if slip.version_id.ssnid:
            return []
        message = slip.env._('%(employee)s : n° CNSS absent.', employee=slip.employee_id.name)
        return [self.issue(message, slip.version_id)]


class MissingNif(CheckRule):
    code = 'GA_NO_NIF'
    severity = WARNING

    def run(self, slip):
        if slip.version_id.l10n_ga_nif:
            return []
        message = slip.env._('%(employee)s : NIF absent.', employee=slip.employee_id.name)
        return [self.issue(message, slip.version_id)]


class MissingBankAccount(CheckRule):
    code = 'GA_NO_BANK'
    severity = WARNING

    def applies(self, slip):
        return slip.version_id.l10n_ga_payment_mode == 'transfer'

    def run(self, slip):
        if slip.employee_id.primary_bank_account_id:
            return []
        message = slip.env._(
            '%(employee)s : payé par virement sans compte bancaire principal.', employee=slip.employee_id.name
        )
        return [self.issue(message, slip.employee_id)]


class LoanInstallmentOverRatio(CheckRule):
    """Échéances de la période > ratio (paramètre daté) du NET du dernier bulletin validé (D-31, D-40)."""

    code = 'GA_LOAN_OVER_RATIO'
    severity = WARNING

    def run(self, slip):
        lines = slip.env['l10n_ga.employee.loan.line'].search(
            [
                ('employee_id', '=', slip.employee_id.id),
                ('company_id', '=', slip.company_id.id),
                ('state', '=', 'to_pay'),
                ('loan_id.state', 'in', ('approved', 'running')),
                ('due_date', '>=', slip.date_from),
                ('due_date', '<=', slip.date_to),
            ]
        )
        installment = sum(lines.mapped('amount'))
        if not installment:
            return []
        reference = slip.env['hr.payslip'].search(
            [
                ('employee_id', '=', slip.employee_id.id),
                ('company_id', '=', slip.company_id.id),
                ('state', 'in', VALIDATED_STATES),
                ('date_to', '<', slip.date_from),
            ],
            order='date_to desc, id desc',
            limit=1,
        )
        net = sum(reference.line_ids.filtered(lambda line: line.code == 'NET').mapped('total'))
        ratio = slip._rule_parameter('l10n_ga_loan_max_installment_ratio')
        facts = LoanFacts(seniority_years=0, installment=installment, reference_net=net, outstanding=0, amount=0)
        failure = MaxInstallmentRatio(ratio).failure(facts)
        if failure is None:
            return []
        message = slip.env._(
            '%(employee)s : échéances de prêt %(installment)s au-delà de %(limit)s (plafond sur le net de référence).',
            employee=slip.employee_id.name,
            installment=installment,
            limit=failure.limit,
        )
        return [self.issue(message, lines.loan_id[:1])]


PAYROLL_CHECKS = (
    NoVersionOnPeriod(),
    MissingHireDate(),
    MissingMarital(),
    ForcedPartsWithoutReason(),
    WageBelowGradeMinimum(),
    AllowanceForcedWithoutReason(),
    MissingCnssNumber(),
    MissingNif(),
    MissingBankAccount(),
    LoanInstallmentOverRatio(),
)


def run_checks(slip, checks=PAYROLL_CHECKS):
    """Enchaîne les contrôles applicables au bulletin."""
    issues = []
    for check in checks:
        if check.applies(slip):
            issues += check.run(slip)
    return issues
