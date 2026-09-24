"""Adaptateur du bulletin Odoo vers le noyau fiscal (patron 2, anti-corruption) et bulletin figé (F7, F16).

Les règles fiscales tiennent en une ligne : ``payslip._l10n_ga_compute(<valeur>, categories, result_rules)``.
Le ``PayResult`` est calculé une fois par bulletin et par jeu de faits (cache dans ``cr.cache``),
purgé en tête de chaque calcul. À la validation, les valeurs imprimées et déclarées sont figées
depuis les lignes du bulletin : un bulletin validé ne relit plus jamais les paramètres.
"""

from collections import defaultdict
from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command

from ..lib.ga_fiscal_core.benefits import benefit_code
from ..lib.ga_fiscal_core.engine import PayslipFacts, compute
from ..lib.ga_fiscal_core.exemptions import GainLine
from ..lib.ga_fiscal_core.labour import GAIN_VALUES, completed_years, leave_allowance, overtime_amount
from ..lib.ga_fiscal_core.loans import seizable_portion
from ..lib.ga_fiscal_core.rounding import CASH_ADJUST, CASH_PAY, CASH_PREV, CASH_VALUES, cash_round, round_fcfa
from ..lib.ga_fiscal_core.treatment import NONE, social_group, tax_group
from .l10n_ga_payroll_check import BLOCKING

GA_CODE = 'GA'
AIK_CATEGORY = 'GA_AIK'
BASIC_CATEGORY = 'BASIC'
BENEFIT_PREFIX = 'benefit:'
CACHE_KEY = 'l10n_ga_hr_payroll.payslip'
VALIDATED_STATES = ('validated', 'paid')  # sprint 0 point 3 : pas d'état « done » en 19
OVERTIME_PREFIX = 'overtime:'
ALLOWANCE_PAY_MODE = 'allowance'  # congé payé : hors BASIC, payé par GA_CONGE (F4)
MONTHS_PER_YEAR = 12  # période de référence de l'allocation de congé et droits annuels (base 05 §5)
LOAN_INPUT_XMLID = 'l10n_ga_hr_payroll.input_type_ga_loan'
ACTIVE_LOAN_STATES = ('approved', 'running')
CASH_MODE = 'cash'

# Champ figé du bulletin → attribut de PayResult (montants du mois).
FROZEN_RESULT_FIELDS = {
    'l10n_ga_gross': 'gains',
    'l10n_ga_benefits_in_kind': 'benefits_in_kind',
    'l10n_ga_social_base': 'social_base',
    'l10n_ga_taxable_gross': 'taxable_gross',
    'l10n_ga_tcs_base': 'tcs_base',
    'l10n_ga_irpp_base': 'irpp_base_monthly',
    'l10n_ga_social_excluded': 'social_excluded',
    'l10n_ga_tax_exempt': 'tax_exempt',
    'l10n_ga_bonus_exempted': 'bonus_exempted',
    'l10n_ga_cnss_employee': 'cnss_employee',
    'l10n_ga_cnamgs_employee': 'cnamgs_employee',
    'l10n_ga_tcs': 'tcs',
}
# Cumul annuel (ce bulletin compris) → champ mensuel cumulé.
YTD_FIELDS = {
    'l10n_ga_ytd_gross': 'l10n_ga_gross',
    'l10n_ga_ytd_taxable': 'l10n_ga_taxable_gross',
    'l10n_ga_ytd_irpp_base': 'l10n_ga_irpp_base',
    'l10n_ga_ytd_irpp': 'l10n_ga_irpp_withheld',
    'l10n_ga_ytd_tcs': 'l10n_ga_tcs',
    'l10n_ga_ytd_cnss': 'l10n_ga_cnss_employee',
    'l10n_ga_ytd_bonus_exempt': 'l10n_ga_bonus_exempted',
}


def _one_year_before(day):
    """Même jour un an plus tôt (29 février → 28 février)."""
    try:
        return day.replace(year=day.year - 1)
    except ValueError:
        return day.replace(year=day.year - 1, day=day.day - 1)


def _frozen_amount(string):
    return fields.Monetary(string=string, readonly=True, copy=False)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_ga_payment_date = fields.Date(
        string='Date de paiement',
        compute='_compute_l10n_ga_payment_date',
        store=True,
        readonly=False,
        help='Date de paiement effective : rattache le bulletin à l’ID10 du mois de paiement.',
    )
    # Valeurs figées à la validation (F7)
    l10n_ga_frozen_date = fields.Datetime(string='Figé le', readonly=True, copy=False)
    l10n_ga_tax_parts_used = fields.Float(string='Parts fiscales utilisées', digits=(3, 1), readonly=True, copy=False)
    l10n_ga_marital_used = fields.Char(string='Situation familiale retenue', readonly=True, copy=False)
    l10n_ga_children_used = fields.Integer(string='Enfants retenus', readonly=True, copy=False)
    l10n_ga_cnss_ceiling_used = _frozen_amount('Plafond CNSS appliqué')
    l10n_ga_cnamgs_ceiling_used = _frozen_amount('Plafond CNAMGS appliqué')
    l10n_ga_gross = _frozen_amount('Brut (Gabon)')
    l10n_ga_benefits_in_kind = _frozen_amount('Avantages en nature')
    l10n_ga_social_base = _frozen_amount('Assiette sociale')
    l10n_ga_taxable_gross = _frozen_amount('Brut imposable')
    l10n_ga_tcs_base = _frozen_amount('Base TCS')
    l10n_ga_irpp_base = _frozen_amount('Base IRPP mensuelle')
    l10n_ga_social_excluded = _frozen_amount('Exclu de l’assiette sociale')
    l10n_ga_tax_exempt = _frozen_amount('Exonéré d’impôt')
    l10n_ga_bonus_exempted = _frozen_amount('Gratifications exonérées')
    l10n_ga_cnss_employee = _frozen_amount('CNSS salariale')
    l10n_ga_cnamgs_employee = _frozen_amount('CNAMGS salariale')
    l10n_ga_tcs = _frozen_amount('TCS')
    l10n_ga_irpp_withheld = _frozen_amount('IRPP retenu (régularisation comprise)')
    l10n_ga_ytd_gross = _frozen_amount('Cumul brut')
    l10n_ga_ytd_taxable = _frozen_amount('Cumul imposable')
    l10n_ga_ytd_irpp_base = _frozen_amount('Cumul base IRPP')
    l10n_ga_ytd_irpp = _frozen_amount('Cumul IRPP')
    l10n_ga_ytd_tcs = _frozen_amount('Cumul TCS')
    l10n_ga_ytd_cnss = _frozen_amount('Cumul CNSS salariale')
    l10n_ga_ytd_bonus_exempt = _frozen_amount('Cumul gratifications exonérées')
    l10n_ga_rounding_carry = _frozen_amount('Reliquat d’arrondi reporté')
    l10n_ga_issue_ids = fields.One2many('l10n_ga.check.issue', 'payslip_id', string='Anomalies Gabon')
    l10n_ga_is_ga = fields.Boolean(compute='_compute_l10n_ga_is_ga')

    @api.depends('date_to', 'payslip_run_id.l10n_ga_payment_date')
    def _compute_l10n_ga_payment_date(self):
        for slip in self:
            slip.l10n_ga_payment_date = slip.payslip_run_id.l10n_ga_payment_date or slip.date_to

    @api.depends('struct_id.country_id')
    def _compute_l10n_ga_is_ga(self):
        for slip in self:
            slip.l10n_ga_is_ga = slip.struct_id.country_id.code == GA_CODE

    # --- lecture du bulletin -------------------------------------------------------------------

    def _l10n_ga_params(self):
        """``FiscalParams`` à la date de fin du bulletin (D-06), options de la société comprises."""
        self.ensure_one()
        return self.company_id._l10n_ga_fiscal_params(self.date_to, raise_if_not_found=True)

    def _l10n_ga_paid_ratio(self):
        """Part payée du mois : même proratisation que ``BASIC`` (``paid_amount`` / salaire)."""
        self.ensure_one()
        wage = self._get_contract_wage()
        if not wage:
            return 1.0
        return min(1.0, max(0.0, self.paid_amount / wage))

    def _l10n_ga_days_worked(self):
        """Jours de présence (prestations de travail, hors absences) : exonération transport journalière."""
        self.ensure_one()
        return sum(line.number_of_days for line in self.worked_days_line_ids if not line.work_entry_type_id.is_leave)

    def _l10n_ga_ytd_domain(self):
        self.ensure_one()
        return [
            ('employee_id', '=', self.employee_id.id),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', VALIDATED_STATES),
            ('date_to', '>=', date(self.date_to.year, 1, 1)),
            ('date_to', '<', self.date_from),
            ('id', '!=', self.id),
        ]

    def _l10n_ga_ytd_opening(self):
        """Cumul d'ouverture de l'année (F12, RG25), s'il couvre une période antérieure au bulletin."""
        self.ensure_one()
        return self.env['l10n_ga.ytd.opening'].search(
            [
                ('employee_id', '=', self.employee_id.id),
                ('company_id', '=', self.company_id.id),
                ('year', '=', self.date_to.year),
                ('date_to', '<', self.date_from),
            ],
            limit=1,
        )

    def _l10n_ga_ytd(self, field_name):
        """Cumul d'un champ figé : cumul d'ouverture + bulletins validés antérieurs de l'année civile."""
        self.ensure_one()
        [(total,)] = self.env['hr.payslip']._read_group(self._l10n_ga_ytd_domain(), aggregates=[f'{field_name}:sum'])
        opening = self._l10n_ga_ytd_opening()
        return (total or 0.0) + (opening._value(field_name) if opening else 0.0)

    def _l10n_ga_previous_carry(self):
        """Reliquat d'arrondi du dernier bulletin validé du salarié (F2, RG23)."""
        self.ensure_one()
        previous = self.env['hr.payslip'].search(
            [
                ('employee_id', '=', self.employee_id.id),
                ('company_id', '=', self.company_id.id),
                ('state', 'in', VALIDATED_STATES),
                ('date_to', '<', self.date_from),
                ('id', '!=', self.id),
            ],
            order='date_to desc, id desc',
            limit=1,
        )
        return previous.l10n_ga_rounding_carry

    def _l10n_ga_cash(self, net):
        """Arrondi espèces (patron 15, D-44) : ``(reliquat précédent, CashRounding)``.

        Pas = arrondi société en espèces, 0 sinon (le reliquat antérieur est alors versé) ;
        au départ du salarié (solde de tout compte), tout est versé.
        """
        static = self._l10n_ga_static()
        if 'cash_prev' not in static:
            static['cash_prev'] = self._l10n_ga_previous_carry()
        step = static['params'].cash_rounding if self.version_id.l10n_ga_payment_mode == CASH_MODE else 0
        previous = static['cash_prev']
        return previous, cash_round(net, previous, int(step), final=self._l10n_ga_is_departure())

    def _l10n_ga_cash_value(self, code, net):
        previous, rounding = self._l10n_ga_cash(net)
        if code == CASH_PREV:
            return round_fcfa(previous)
        if code == CASH_ADJUST:
            return rounding.paid - round_fcfa(net) - round_fcfa(previous)
        if code == CASH_PAY:
            return rounding.paid
        raise ValueError(f'Valeur d’arrondi inconnue : {code!r}')

    def _l10n_ga_regularize(self):
        """Régularisation annuelle de l'IRPP : dernier bulletin de l'année ou départ dans la période."""
        self.ensure_one()
        if (self.date_to + timedelta(days=1)).year != self.date_to.year:
            return True
        return self._l10n_ga_is_departure()

    def _l10n_ga_is_departure(self):
        """Départ ou fin de contrat dans la période : régularisation IRPP, solde des prêts."""
        self.ensure_one()
        end = self.version_id.departure_date or self.version_id.contract_date_end
        return bool(end and self.date_from <= end <= self.date_to)

    def _l10n_ga_static(self):
        """Données fixes pendant un calcul : paramètres, version, cumuls, présence."""
        self.ensure_one()
        cache = self.env.cr.cache.setdefault(CACHE_KEY, {})
        entry = cache.get(self.id)
        if entry is None:
            version = self.version_id
            trips = version.l10n_ga_transport_trips
            entry = cache[self.id] = {
                'params': self._l10n_ga_params(),
                'paid_ratio': self._l10n_ga_paid_ratio(),
                'facts': {
                    'benefits': version._l10n_ga_benefit_kinds(),
                    'marital': version.marital,
                    'children': version.children,
                    'disabled_children': version.l10n_ga_disabled_children,
                    'extra_half_part': version.l10n_ga_extra_half_part,
                    'forced_parts': version.l10n_ga_tax_parts_forced or None,
                    'presence_days': self._l10n_ga_days_worked(),
                    'transport_trips': int(trips) if trips else None,
                    'has_company_car': version.l10n_ga_company_car,
                    'ytd_bonus_exempted': self._l10n_ga_ytd('l10n_ga_bonus_exempted'),
                    'ytd_irpp_base': self._l10n_ga_ytd('l10n_ga_irpp_base'),
                    'ytd_irpp_withheld': self._l10n_ga_ytd('l10n_ga_irpp_withheld'),
                    'regularize': self._l10n_ga_regularize(),
                },
                'forced_shares': self._l10n_ga_forced_shares(),
                'results': {},
            }
        return entry

    def _l10n_ga_clear_cache(self):
        cache = self.env.cr.cache.get(CACHE_KEY)
        if cache:
            for slip_id in self.ids:
                cache.pop(slip_id, None)

    def _l10n_ga_forced_shares(self):
        """Part des entrées forcées imposables par code d'entrée (F15, D-36)."""
        self.ensure_one()
        totals = defaultdict(float)
        forced = defaultdict(float)
        for line in self.input_line_ids:
            totals[line.code] += line.amount
            if line.l10n_ga_forced_taxable:
                forced[line.code] += line.amount
        return {code: forced[code] / totals[code] for code in forced if totals[code]}

    def _l10n_ga_gain_lines(self, totals):
        """Une ``GainLine`` par rubrique de gain en espèces de la structure (``totals`` : code → total).

        Une rubrique dont une partie des entrées est forcée imposable est scindée en deux lignes
        de même code (part normale, part forcée), D-36.
        """
        self.ensure_one()
        forced_shares = self._l10n_ga_static()['forced_shares']
        lines = []
        for rule in self.struct_id.rule_ids.sorted(lambda r: (r.sequence, r.id)):
            if rule.l10n_ga_social_base in (False, NONE) or rule.category_id.code == AIK_CATEGORY:
                continue
            amount = totals.get(rule.code, 0.0)
            if not amount:
                continue
            groups = (
                social_group(rule.l10n_ga_social_base, rule.l10n_ga_social_cap_group or None),
                tax_group(rule.l10n_ga_tax_base, rule.l10n_ga_tax_cap_group or None),
            )
            forced = round_fcfa(amount * forced_shares.get(rule.code, 0))
            for part, is_forced in ((amount - forced, False), (forced, True)):
                if part:
                    lines.append(GainLine(rule.code, part, *groups, forced_taxable=is_forced))
        return tuple(lines)

    def _l10n_ga_facts(self, main_salary, totals):
        """Traduit le bulletin en ``PayslipFacts`` (``totals`` : code de règle → total)."""
        static = self._l10n_ga_static()
        return PayslipFacts(
            lines=self._l10n_ga_gain_lines(totals),
            main_salary=main_salary,
            presence_ratio=static['paid_ratio'],
            **static['facts'],
        )

    def _l10n_ga_result(self, main_salary, totals):
        static = self._l10n_ga_static()
        facts = self._l10n_ga_facts(main_salary, totals)
        result = static['results'].get(facts)
        if result is None:
            result = static['results'][facts] = compute(facts, static['params'])
        return result

    @staticmethod
    def _l10n_ga_value(result, code):
        """Montant de ``PayResult`` désigné par ``code`` (attribut, ou ``benefit:<nature>``)."""
        if code.startswith(BENEFIT_PREFIX):
            line_code = benefit_code(code.removeprefix(BENEFIT_PREFIX))
            return next((line.amount for line in result.lines if line.code == line_code), 0)
        if code not in result.__dataclass_fields__:
            raise ValueError(f'Valeur du noyau inconnue : {code!r}')
        return getattr(result, code)

    # --- gains calculés avant le PayResult (étape 2.4) -------------------------------------------

    def _l10n_ga_seniority_bonus(self):
        """Prime d'ancienneté du mois complet (proratisée ensuite par la règle, RG04, D-25)."""
        self.ensure_one()
        version = self.version_id
        agreement = version.l10n_ga_agreement_id
        if not agreement:
            return 0
        rate = agreement._seniority_rate_at(version._l10n_ga_seniority_start(), self.date_to)
        base = version.wage
        if agreement.seniority_base == 'grade_minimum':
            base = version._l10n_ga_grade_minimum(self.date_to) or base
        return round_fcfa(base * rate)

    def _l10n_ga_hourly_rate(self):
        """Taux horaire des heures supplémentaires : salaire / heures mensuelles de référence (base 05 §2)."""
        self.ensure_one()
        if self.wage_type == 'hourly':
            return self.version_id.hourly_wage
        return self.version_id.contract_wage / self._rule_parameter('l10n_ga_hours_month_ref')

    def _l10n_ga_overtime_hours(self, period):
        self.ensure_one()
        return sum(
            line.number_of_hours
            for line in self.worked_days_line_ids
            if line.work_entry_type_id.l10n_ga_overtime_period == period
        )

    def _l10n_ga_overtime(self, period):
        """Heures supplémentaires d'une période, majorées selon la convention (aucun taux par défaut)."""
        self.ensure_one()
        hours = self._l10n_ga_overtime_hours(period)
        agreement = self.version_id.l10n_ga_agreement_id
        tranches = agreement._overtime_tranches(period) if agreement else ()
        try:
            return overtime_amount(self._l10n_ga_hourly_rate() if hours else 0, hours, tranches)
        except ValueError as error:
            raise UserError(self._l10n_ga_overtime_message(period, error)) from error

    def _l10n_ga_overtime_message(self, period, error):
        return self.env._(
            '%(employee)s : heures supplémentaires (%(period)s) — %(detail)s.',
            employee=self.employee_id.name,
            period=dict(self.env['l10n_ga.overtime.rate']._fields['period'].selection)[period],
            detail=error,
        )

    def _l10n_ga_leave_lines(self):
        return self.worked_days_line_ids.filtered(
            lambda line: line.work_entry_type_id.l10n_ga_pay_mode == ALLOWANCE_PAY_MODE
        )

    def _l10n_ga_leave_reference_pay(self):
        """Rémunération « base congés » des bulletins validés des 12 mois précédents (circulaire 565)."""
        self.ensure_one()
        start = _one_year_before(self.date_from)
        [(total,)] = self.env['hr.payslip.line']._read_group(
            [
                ('slip_id.employee_id', '=', self.employee_id.id),
                ('slip_id.company_id', '=', self.company_id.id),
                ('slip_id.state', 'in', VALIDATED_STATES),
                ('slip_id.date_to', '>=', start),
                ('slip_id.date_to', '<', self.date_from),
                ('salary_rule_id.l10n_ga_leave_base', '=', True),
            ],
            aggregates=['total:sum'],
        )
        return total or 0.0

    def _l10n_ga_is_minor(self):
        birthday = self.employee_id.birthday
        majority = self._rule_parameter('l10n_ga_majority_age')
        return bool(birthday) and completed_years(birthday, self.date_to) < majority

    def _l10n_ga_working_days_per_week(self):
        calendar = self.version_id.resource_calendar_id
        return len(set(calendar.attendance_ids.mapped('dayofweek'))) if calendar else 0

    def _l10n_ga_leave_allowance(self):
        """Allocation de congé : plus favorable du maintien et de 1/12 (5/48 mineur) — base 05 §5, D-23."""
        self.ensure_one()
        leave_lines = self._l10n_ga_leave_lines()
        if not leave_lines:
            return 0
        attendance_hours = sum(
            line.number_of_hours for line in self.worked_days_line_ids if not line.work_entry_type_id.is_extra_hours
        )
        share = sum(leave_lines.mapped('number_of_hours')) / attendance_hours if attendance_hours else 0
        # Maintien : salaire et indemnités « base congés » proratisées, au prorata des heures de congé.
        prorated = self.struct_id.rule_ids.filtered(lambda r: r.l10n_ga_prorate and r.l10n_ga_leave_base)
        monthly = self.version_id.contract_wage
        monthly += sum(line.amount for line in self.input_line_ids if line.code in prorated.mapped('code'))
        if 'seniority' in prorated.mapped('l10n_ga_core_value'):
            monthly += self._l10n_ga_gain('seniority')
        minor = self._l10n_ga_is_minor()
        ratio = self._rule_parameter('l10n_ga_leave_ratio_minor' if minor else 'l10n_ga_leave_ratio_adult')
        days_month = self._rule_parameter(
            'l10n_ga_leave_days_month_minor' if minor else 'l10n_ga_leave_days_month_adult'
        )
        working_week = self._rule_parameter('l10n_ga_leave_working_days_week')
        calendar_week = self._l10n_ga_working_days_per_week() or working_week
        days_taken = sum(leave_lines.mapped('number_of_days')) * working_week / calendar_week
        return leave_allowance(
            maintained=monthly * share,
            reference_pay=self._l10n_ga_leave_reference_pay(),
            ratio=ratio,
            days_taken=days_taken,
            annual_days=days_month * MONTHS_PER_YEAR,
        )

    def _l10n_ga_gain(self, code):
        """Gain calculé avant le PayResult (``GAIN_VALUES``), mis en cache pendant le calcul."""
        self.ensure_one()
        gains = self._l10n_ga_static().setdefault('gains', {})
        if code not in gains:
            if code == 'seniority':
                gains[code] = self._l10n_ga_seniority_bonus()
            elif code == 'leave_allowance':
                gains[code] = self._l10n_ga_leave_allowance()
            elif code.startswith(OVERTIME_PREFIX):
                gains[code] = self._l10n_ga_overtime(code.removeprefix(OVERTIME_PREFIX))
            else:
                raise ValueError(f'Gain calculé inconnu : {code!r}')
        return gains[code]

    def _l10n_ga_blocking_issues(self):
        """Anomalies bloquantes Gabon : salaire sous le minimum de la grille (RG18), heures sans taux."""
        self.ensure_one()
        messages = []
        version = self.version_id
        minimum = version._l10n_ga_grade_minimum(self.date_to) if version.l10n_ga_grade_id else 0
        if version.wage < minimum:
            messages.append(
                self.env._(
                    '%(employee)s : salaire %(wage)s inférieur au minimum %(minimum)s de la grille au %(date)s.',
                    employee=self.employee_id.name,
                    wage=version.wage,
                    minimum=minimum,
                    date=self.date_to,
                )
            )
        agreement = version.l10n_ga_agreement_id
        for period, _label in self.env['l10n_ga.overtime.rate']._fields['period'].selection:
            hours = self._l10n_ga_overtime_hours(period)
            try:
                overtime_amount(1, hours, agreement._overtime_tranches(period) if agreement else ())
            except ValueError as error:
                messages.append(self._l10n_ga_overtime_message(period, error))
        return messages

    def _issues_dependencies(self):
        return [
            *super()._issues_dependencies(),
            'version_id.wage',
            'version_id.l10n_ga_grade_id',
            'version_id.l10n_ga_agreement_id',
            'worked_days_line_ids',
            'l10n_ga_issue_ids.severity',
        ]

    def _l10n_ga_issue_entry(self, issue):
        """Anomalie du lot (F8) au format des anomalies natives du bulletin (pont ADR-18 §4)."""
        record = self.env[issue.res_model].browse(issue.res_id) if issue.res_model else self.employee_id
        return {
            'message': issue.message,
            'action_text': self.env._('Corriger'),
            'action': record._get_records_action(target='new'),
            'level': 'danger' if issue.severity == BLOCKING else 'warning',
        }

    def _get_errors_by_slip(self):
        errors_by_slip = super()._get_errors_by_slip()
        for slip in self.filtered(lambda s: s.state == 'draft' and s.l10n_ga_is_ga):
            if slip.version_id:
                for message in slip._l10n_ga_blocking_issues():
                    errors_by_slip[slip].append(
                        {
                            'message': message,
                            'action_text': self.env._('Salarié'),
                            'action': slip.employee_id._get_records_action(name=self.env._('Salarié'), target='new'),
                            'level': 'danger',
                        }
                    )
            for issue in slip.l10n_ga_issue_ids.filtered(lambda i: i.severity == BLOCKING):
                errors_by_slip[slip].append(slip._l10n_ga_issue_entry(issue))
        return errors_by_slip

    def _get_warnings_by_slip(self):
        warnings_by_slip = super()._get_warnings_by_slip()
        for slip in self.filtered(lambda s: s.state == 'draft' and s.l10n_ga_is_ga):
            for issue in slip.l10n_ga_issue_ids.filtered(lambda i: i.severity != BLOCKING):
                warnings_by_slip[slip].append(slip._l10n_ga_issue_entry(issue))
        return warnings_by_slip

    def _l10n_ga_compute(self, code, categories, result_rules):
        """Point d'entrée des règles salariales (une ligne) : gain calculé ou montant du ``PayResult``."""
        self.ensure_one()
        if code in GAIN_VALUES:
            return self._l10n_ga_gain(code)
        if code in CASH_VALUES:
            return self._l10n_ga_cash_value(code, result_rules['NET']['total'])
        totals = {rule_code: values['total'] for rule_code, values in result_rules.items()}
        return self._l10n_ga_value(self._l10n_ga_result(categories[BASIC_CATEGORY], totals), code)

    def _get_payslip_lines(self):
        self._l10n_ga_clear_cache()
        return super()._get_payslip_lines()

    # --- bulletin figé (F7, F16) ---------------------------------------------------------------

    def _l10n_ga_line_totals(self):
        self.ensure_one()
        totals = {}
        for line in self.line_ids:
            totals[line.code] = totals.get(line.code, 0.0) + line.total
        return totals

    def _l10n_ga_main_salary(self):
        basic = self.env.ref('hr_payroll.BASIC')
        return sum(
            line.total
            for line in self.line_ids
            if basic in (line.salary_rule_id.category_id, line.salary_rule_id.category_id.parent_id)
        )

    def _l10n_ga_check_lines(self, result, totals):
        """Refuse le figement si le noyau, rejoué, ne retrouve pas les montants des lignes."""
        for rule in self.struct_id.rule_ids.filtered('l10n_ga_core_value'):
            expected = rule._l10n_ga_sign() * self._l10n_ga_expected(rule, result, totals)
            if abs(totals.get(rule.code, 0.0) - expected) >= 1:
                raise UserError(
                    self.env._(
                        'Bulletin %(slip)s : la ligne %(code)s ne correspond plus au calcul '
                        '(%(line)s au lieu de %(expected)s). Un paramètre a changé depuis le calcul : '
                        'recalculez le bulletin avant de le valider.',
                        slip=self.name,
                        code=rule.code,
                        line=totals.get(rule.code, 0.0),
                        expected=expected,
                    )
                )

    def _l10n_ga_expected(self, rule, result, totals):
        """Montant attendu d'une règle liée au noyau (gain proratisé comme dans ``_compute_rule``)."""
        code = rule.l10n_ga_core_value
        if code in CASH_VALUES:
            return self._l10n_ga_cash_value(code, totals.get('NET', 0.0))
        if code not in GAIN_VALUES:
            return self._l10n_ga_value(result, code)
        amount = self._l10n_ga_gain(code)
        if rule.l10n_ga_prorate and amount:
            amount = round_fcfa(amount * self._l10n_ga_paid_ratio())
        return amount

    def _l10n_ga_line_codes(self):
        """Code de ligne du noyau → code de règle (les avantages en nature sont nommés par le noyau)."""
        mapping = {}
        for rule in self.struct_id.rule_ids.filtered('l10n_ga_core_value'):
            if rule.l10n_ga_core_value.startswith(BENEFIT_PREFIX):
                mapping[benefit_code(rule.l10n_ga_core_value.removeprefix(BENEFIT_PREFIX))] = rule.code
        return mapping

    def _l10n_ga_freeze_lines(self, result):
        """Parts exclue sociale et exonérée fiscale par ligne (F16), réparties entre lignes de même code."""
        codes = self._l10n_ga_line_codes()
        by_code = defaultdict(lambda: [0, 0])  # une rubrique scindée (D-36) a plusieurs lignes du noyau
        for exemption in result.lines:
            parts = by_code[codes.get(exemption.code, exemption.code)]
            parts[0] += exemption.social_excluded
            parts[1] += exemption.tax_exempt
        for code, (social_excluded, tax_exempt) in by_code.items():
            lines = self.line_ids.filtered(lambda line, code=code: line.code == code)
            total = sum(lines.mapped('total'))
            remaining = {
                'l10n_ga_social_excluded': social_excluded,
                'l10n_ga_tax_exempt': tax_exempt,
            }
            for index, line in enumerate(lines):
                values = {}
                for field_name, amount in list(remaining.items()):
                    if index == len(lines) - 1 or not total:
                        values[field_name] = amount
                    else:
                        values[field_name] = round_fcfa(amount * line.total / total)
                    remaining[field_name] = amount - values[field_name]
                line.write(values)

    def _l10n_ga_freeze(self):
        """Stocke les valeurs imprimées et déclarées du bulletin (F7), depuis ses lignes."""
        for slip in self.filtered(lambda s: s.l10n_ga_is_ga and s.state == 'draft' and s.line_ids):
            slip._l10n_ga_clear_cache()
            issues = slip._l10n_ga_blocking_issues()
            if issues:
                raise UserError('\n'.join(issues))
            totals = slip._l10n_ga_line_totals()
            result = slip._l10n_ga_result(slip._l10n_ga_main_salary(), totals)
            slip._l10n_ga_check_lines(result, totals)
            params = slip._l10n_ga_static()['params']
            values = {field_name: getattr(result, attr) for field_name, attr in FROZEN_RESULT_FIELDS.items()}
            values.update(
                l10n_ga_irpp_withheld=result.irpp + result.irpp_regularisation,
                l10n_ga_tax_parts_used=result.tax_parts,
                l10n_ga_marital_used=slip.version_id.marital,
                l10n_ga_children_used=slip.version_id.children,
                l10n_ga_cnss_ceiling_used=params.cnss_ceiling,
                l10n_ga_cnamgs_ceiling_used=params.cnamgs_ceiling,
                l10n_ga_frozen_date=fields.Datetime.now(),
                l10n_ga_rounding_carry=-totals.get('GA_ROUND', 0.0),
            )
            for ytd_field, month_field in YTD_FIELDS.items():
                values[ytd_field] = slip._l10n_ga_ytd(month_field) + values[month_field]
            slip.write(values)
            slip._l10n_ga_freeze_lines(result)
            slip._l10n_ga_clear_cache()

    def action_payslip_done(self):
        # Avant super() : bulletin encore en brouillon, lignes calculées (sprint 0 point 13).
        self._l10n_ga_freeze()
        result = super().action_payslip_done()
        self._l10n_ga_withhold_loan_lines()
        return result

    def action_payslip_cancel(self):
        result = super().action_payslip_cancel()
        self._l10n_ga_release_loan_lines()
        return result

    def action_payslip_draft(self):
        result = super().action_payslip_draft()
        self._l10n_ga_release_loan_lines()
        return result

    # --- indemnités récurrentes (F15, ADR-16) ----------------------------------------------------

    def _l10n_ga_valid_allowances(self):
        """Indemnités Gabon ouvertes dont la validité recoupe la période (même filtre que le standard)."""
        self.ensure_one()
        return self.employee_id.salary_attachment_ids.filtered(
            lambda a: (
                a.state == 'open'
                and a.l10n_ga_is_allowance
                and a.date_start <= self.date_to
                and (not a.date_end or a.date_end >= self.date_from)
                and (not a.other_input_type_id.struct_ids or self.struct_id in a.other_input_type_id.struct_ids)
            )
        )

    def _l10n_ga_allowance_inputs(self, manual_priority=True):
        """Une entrée par indemnité, marquée ``l10n_ga_allowance_id`` (prorata de validité, D-35).

        ``manual_priority`` (calcul du bulletin) : une entrée non marquée du même type est une saisie
        manuelle et remplace l'automatique. Sinon (après ``_compute_input_line_ids`` standard), les
        entrées non marquées sont l'entrée groupée du standard et sont remplacées.
        """
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                continue
            allowances = slip._l10n_ga_valid_allowances()
            types = allowances.other_input_type_id
            unmarked = slip.input_line_ids.filtered(
                lambda line, types=types: line.input_type_id in types and not line.l10n_ga_allowance_id
            )
            commands = [Command.unlink(line.id) for line in slip.input_line_ids.filtered('l10n_ga_allowance_id')]
            if manual_priority:
                manual_types = unmarked.input_type_id
            else:
                commands += [Command.unlink(line.id) for line in unmarked]
                manual_types = self.env['hr.payslip.input.type']
            for allowance in allowances.filtered(lambda a, manual=manual_types: a.other_input_type_id not in manual):
                amount = allowance._l10n_ga_amount(slip)
                if amount:
                    commands.append(
                        Command.create(
                            {
                                'name': allowance.description or allowance.other_input_type_id.name,
                                'amount': amount,
                                'input_type_id': allowance.other_input_type_id.id,
                                'l10n_ga_allowance_id': allowance.id,
                                'l10n_ga_forced_taxable': allowance.l10n_ga_forced_taxable,
                            }
                        )
                    )
            if commands:
                slip.update({'input_line_ids': commands})

    def _compute_input_line_ids(self):
        result = super()._compute_input_line_ids()
        self.filtered(lambda s: s.state == 'draft' and s.l10n_ga_is_ga)._l10n_ga_allowance_inputs(manual_priority=False)
        return result

    # --- prêts (F1, RG21) ------------------------------------------------------------------------

    def _l10n_ga_due_loan_lines(self):
        """Échéances à retenir : celles de la période, ou tout le restant dû au départ du salarié."""
        self.ensure_one()
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'to_pay'),
            ('payslip_id', '=', False),
            ('loan_id.state', 'in', ACTIVE_LOAN_STATES),
        ]
        if not self._l10n_ga_is_departure():
            domain += [('due_date', '>=', self.date_from), ('due_date', '<=', self.date_to)]
        lines = self.env['l10n_ga.employee.loan.line'].search(domain)
        # RG21 : une échéance déjà reprise par un autre bulletin non annulé n'est pas reprise deux fois.
        taken = self.env['hr.payslip.input'].search(
            [
                ('l10n_ga_loan_line_id', 'in', lines.ids),
                ('payslip_id', '!=', self.id),
                ('payslip_id.state', '!=', 'cancel'),
            ]
        )
        return lines - taken.l10n_ga_loan_line_id

    def _l10n_ga_loan_inputs(self):
        """Entrées ``GA_LOAN`` du bulletin brouillon, une par échéance (sprint 0 point 6)."""
        loan_type = self.env.ref(LOAN_INPUT_XMLID)
        for slip in self:
            commands = [Command.unlink(line.id) for line in slip.input_line_ids.filtered('l10n_ga_loan_line_id')]
            for line in slip._l10n_ga_due_loan_lines():
                commands.append(
                    Command.create(
                        {
                            'name': self.env._(
                                '%(loan)s — échéance du %(date)s', loan=line.loan_id.name, date=line.due_date
                            ),
                            'amount': line.amount,
                            'input_type_id': loan_type.id,
                            'l10n_ga_loan_line_id': line.id,
                        }
                    )
                )
            if commands:
                slip.write({'input_line_ids': commands})

    def _l10n_ga_cap_departure_loan(self):
        """Solde de tout compte : retenue du prêt plafonnée à la quotité saisissable (D-32).

        Base = net du bulletin avant la retenue du prêt. L'échéance qui dépasse est scindée ;
        le surplus reste « à payer ». Retourne vrai si le bulletin doit être recalculé.
        """
        self.ensure_one()
        inputs = self.input_line_ids.filtered('l10n_ga_loan_line_id')
        if not inputs or not self._l10n_ga_is_departure():
            return False
        total = sum(inputs.mapped('amount'))
        net = sum(self.line_ids.filtered(lambda line: line.code == 'NET').mapped('total'))
        remaining = seizable_portion(net + total, self._rule_parameter('l10n_ga_seizable_brackets'))
        if total <= remaining:
            return False
        commands = []
        for entry in inputs.sorted(lambda i: (i.l10n_ga_loan_line_id.due_date, i.id)):
            line = entry.l10n_ga_loan_line_id
            if entry.amount <= remaining:
                remaining -= entry.amount
            elif remaining > 0:
                line.copy({'amount': line.amount - remaining, 'due_date': line.due_date})
                line.amount = remaining
                commands.append(Command.update(entry.id, {'amount': remaining}))
                remaining = 0
            else:
                commands.append(Command.unlink(entry.id))
        self.write({'input_line_ids': commands})
        return True

    def compute_sheet(self):
        ga_slips = self.filtered(lambda s: s.state == 'draft' and s.l10n_ga_is_ga)
        # RG26, D-38 : contrôles du lot avant calcul ; un lot bloqué n'est pas calculé.
        ga_slips.payslip_run_id._l10n_ga_run_checks()
        blocked = ga_slips.filtered(lambda s: s.payslip_run_id.l10n_ga_blocking_count)
        blocked.line_ids.unlink()
        ga_slips -= blocked
        ga_slips._l10n_ga_allowance_inputs()
        ga_slips._l10n_ga_loan_inputs()
        result = super(HrPayslip, self - blocked).compute_sheet()
        capped = ga_slips.filtered(lambda s: s._l10n_ga_cap_departure_loan())
        if capped:
            super(HrPayslip, capped).compute_sheet()
        return result

    def _l10n_ga_withhold_loan_lines(self):
        """À la validation (D-30) : échéances du bulletin « retenues » (RG21)."""
        for slip in self.filtered(lambda s: s.state in VALIDATED_STATES):
            for entry in slip.input_line_ids.filtered('l10n_ga_loan_line_id'):
                line = entry.l10n_ga_loan_line_id
                if line.state != 'to_pay' or (line.payslip_id and line.payslip_id != slip):
                    raise UserError(
                        self.env._(
                            'L’échéance du %(date)s du prêt %(loan)s est déjà retenue ou n’est plus due.',
                            date=line.due_date,
                            loan=line.loan_id.name,
                        )
                    )
                if abs(entry.amount - line.amount) >= 1:
                    raise UserError(
                        self.env._(
                            'Bulletin %(slip)s : le montant de l’échéance du prêt %(loan)s a été modifié : '
                            'recalculez le bulletin.',
                            slip=slip.name,
                            loan=line.loan_id.name,
                        )
                    )
                line.write({'state': 'withheld', 'payslip_id': slip.id})
            loans = slip.input_line_ids.l10n_ga_loan_line_id.loan_id
            loans._update_state()
            if slip._l10n_ga_is_departure():
                for loan in loans.filtered(lambda loan: loan.remaining_amount):
                    loan.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=loan.create_uid.id or self.env.uid,
                        note=self.env._(
                            'Départ du salarié : %(amount)s restent dus au-delà de la quotité saisissable.',
                            amount=loan.remaining_amount,
                        ),
                    )

    def _l10n_ga_release_loan_lines(self):
        """Annulation ou retour en brouillon : les échéances retenues redeviennent « à payer »."""
        lines = self.env['l10n_ga.employee.loan.line'].search([('payslip_id', 'in', self.ids)])
        if lines:
            lines.write({'state': 'to_pay', 'payslip_id': False})
            lines.loan_id._update_state()
