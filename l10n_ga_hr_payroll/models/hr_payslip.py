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

from ..lib.ga_fiscal_core import print_layout as layout
from ..lib.ga_fiscal_core.basic import DEDUCT, basic_amount, basic_quantity, hourly_rate
from ..lib.ga_fiscal_core.benefits import benefit_code
from ..lib.ga_fiscal_core.engine import PayslipFacts, compute
from ..lib.ga_fiscal_core.exemptions import GainLine
from ..lib.ga_fiscal_core.labour import GAIN_VALUES, completed_years, leave_allowance, overtime_amount
from ..lib.ga_fiscal_core.loans import seizable_portion
from ..lib.ga_fiscal_core.print_bases import print_bases
from ..lib.ga_fiscal_core.rounding import CASH_ADJUST, CASH_PAY, CASH_PREV, CASH_VALUES, cash_round, round_fcfa
from ..lib.ga_fiscal_core.treatment import NONE, social_group, tax_group
from .hr_version import PAYMENT_MODE_SELECTION
from .l10n_ga_payroll_check import BLOCKING, PAYROLL_CHECKS

GA_CODE = 'GA'
AIK_CATEGORY = 'GA_AIK'
BASIC_CATEGORY = 'BASIC'
BENEFIT_PREFIX = 'benefit:'
CACHE_KEY = 'l10n_ga_hr_payroll.payslip'
VALIDATED_STATES = ('validated', 'paid')  # sprint 0 point 3 : pas d'état « done » en 19
BASIC_CODE = 'BASIC'
OUT_OF_CONTRACT = 'OUT'  # prestation hors contrat (E/hr_payroll/models/hr_payslip.py:951)
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
    'l10n_ga_fnh_employer': 'fnh',
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
    'l10n_ga_ytd_contributions': 'l10n_ga_employee_contributions',
    'l10n_ga_ytd_benefits': 'l10n_ga_benefits_in_kind',
    'l10n_ga_ytd_fnh': 'l10n_ga_fnh_employer',
    'l10n_ga_ytd_tax_exempt': 'l10n_ga_tax_exempt',
}
LEAVE_TYPE_XMLID = 'l10n_ga_hr_payroll.leave_type_ga_cp'


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
    # Bulletin imprimé (plan 2.7 b) : salaire contractuel, organisme FNH, cumuls et congés figés.
    l10n_ga_wage = _frozen_amount('Salaire contractuel (figé)')
    l10n_ga_employee_contributions = _frozen_amount('Cotisations salariales')
    l10n_ga_fnh_employer = _frozen_amount('FNH patronal')
    l10n_ga_ytd_contributions = _frozen_amount('Cumul cotisations salariales')
    l10n_ga_ytd_benefits = _frozen_amount('Cumul avantages en nature')
    l10n_ga_ytd_fnh = _frozen_amount('Cumul FNH patronal')
    l10n_ga_ytd_tax_exempt = _frozen_amount('Cumul indemnités non imposables')
    l10n_ga_leave_base = _frozen_amount('Base congés (12 mois)')
    l10n_ga_leave_acquired = fields.Float(string='Congés acquis (jours)', readonly=True, copy=False)
    l10n_ga_leave_taken = fields.Float(string='Congés pris (jours)', readonly=True, copy=False)
    l10n_ga_leave_balance = fields.Float(string='Solde de congés (jours)', readonly=True, copy=False)
    l10n_ga_employee_city = fields.Char(string='Ville du salarié (figée)', readonly=True, copy=False)
    l10n_ga_direction = fields.Char(string='Direction (figée)', readonly=True, copy=False)
    # Identité imprimée, figée à la validation (RG24, D-48) : une fiche modifiée ne change pas un ancien bulletin.
    l10n_ga_employee_name = fields.Char(string='Salarié (figé)', readonly=True, copy=False)
    l10n_ga_registration_number = fields.Char(string='Matricule (figé)', readonly=True, copy=False)
    l10n_ga_job_title = fields.Char(string='Emploi (figé)', readonly=True, copy=False)
    l10n_ga_department = fields.Char(string='Service (figé)', readonly=True, copy=False)
    l10n_ga_grade = fields.Char(string='Catégorie (figée)', readonly=True, copy=False)
    l10n_ga_hire_date = fields.Date(string='Date d’embauche (figée)', readonly=True, copy=False)
    l10n_ga_seniority_date = fields.Date(string='Date d’ancienneté (figée)', readonly=True, copy=False)
    l10n_ga_ssnid = fields.Char(string='N° CNSS (figé)', readonly=True, copy=False)
    l10n_ga_cnamgs_number = fields.Char(string='N° CNAMGS (figé)', readonly=True, copy=False)
    l10n_ga_nif = fields.Char(string='NIF (figé)', readonly=True, copy=False)
    l10n_ga_payment_mode = fields.Selection(
        PAYMENT_MODE_SELECTION, string='Mode de paiement (figé)', readonly=True, copy=False
    )
    l10n_ga_bank_name = fields.Char(string='Banque (figée)', readonly=True, copy=False)
    l10n_ga_bank_account = fields.Char(string='Compte bancaire (figé)', readonly=True, copy=False)
    l10n_ga_company_nif = fields.Char(string='NIF employeur (figé)', readonly=True, copy=False)
    l10n_ga_company_cnss = fields.Char(string='N° CNSS employeur (figé)', readonly=True, copy=False)
    l10n_ga_company_cnamgs = fields.Char(string='N° CNAMGS employeur (figé)', readonly=True, copy=False)
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
        """Part payée du mois : même proratisation que ``BASIC`` (salaire de base payé / salaire)."""
        self.ensure_one()
        wage = self._get_contract_wage()
        if not wage:
            return 1.0
        return min(1.0, max(0.0, self._l10n_ga_basic_amount() / wage))

    # --- salaire de base sur le mois de référence (FIX 01, arrêté 016/MTEPS art. 5, base 05 §2) ----

    def _l10n_ga_reference_hours(self):
        """Heures mensuelles de référence (paramètre daté l10n_ga_hours_month_ref) : base unique du taux horaire."""
        return self._rule_parameter('l10n_ga_hours_month_ref')

    def _l10n_ga_uses_reference_hours(self):
        return self.wage_type != 'hourly' and self.struct_id.use_worked_day_lines

    def _l10n_ga_basic_hours(self):
        """Heures payées par le salaire de base : référence − heures non payées (jamais négatives).

        Heures non payées : prestations du contrat non payées par la base (``is_paid`` faux : absences non
        rémunérées, congé payé réglé par l'allocation, CNSS sans subrogation) et heures hors contrat
        (``OUT``, E/hr_payroll/models/hr_payslip.py:920-959) selon l'option société (D-104).
        """
        self.ensure_one()
        lines = self._l10n_ga_month_lines()
        out_hours = sum(lines.filtered(lambda wd: wd.code == OUT_OF_CONTRACT).mapped('number_of_hours'))
        unpaid = sum(lines.filtered(lambda wd: wd.code != OUT_OF_CONTRACT and not wd.is_paid).mapped('number_of_hours'))
        planned = sum(lines.mapped('number_of_hours'))
        method = self.company_id.l10n_ga_entry_exit_hours or DEDUCT
        return basic_quantity(self._l10n_ga_reference_hours(), unpaid, out_hours, planned, method=method)

    def _l10n_ga_basic_amount(self):
        """Montant de ``BASIC`` : salaire exact sur un mois complet, sinon heures payées × taux horaire."""
        self.ensure_one()
        if not self._l10n_ga_uses_reference_hours():
            return self.paid_amount  # salaire horaire ou structure sans prestations : standard
        return basic_amount(self._get_contract_wage(), self._l10n_ga_reference_hours(), self._l10n_ga_basic_hours())

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
        return hourly_rate(self.version_id.contract_wage, self._l10n_ga_reference_hours())

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
        # Même base horaire que la ligne de base (FIX 01) : heures de congé / heures de référence.
        share = min(1.0, sum(leave_lines.mapped('number_of_hours')) / self._l10n_ga_reference_hours())
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

    def _l10n_ga_payroll_checks(self):
        """Chaîne des contrôles avant paie (F8), complétée par les modules supérieurs (patron 8)."""
        return PAYROLL_CHECKS

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

    def _l10n_ga_identity(self):
        """Identité imprimée lue sur la fiche du jour (figée à la validation, D-48)."""
        self.ensure_one()
        version = self.version_id
        employee = self.employee_id
        bank = employee.primary_bank_account_id
        return {
            'l10n_ga_employee_name': employee.name,
            'l10n_ga_registration_number': employee.registration_number or False,
            'l10n_ga_job_title': version.job_title or version.job_id.name or False,
            'l10n_ga_department': version.department_id.name or False,
            'l10n_ga_direction': version.department_id.parent_id.name or False,
            'l10n_ga_employee_city': version.private_city or False,
            'l10n_ga_wage': version.contract_wage,
            'l10n_ga_grade': version.l10n_ga_grade_id.display_name or False,
            'l10n_ga_hire_date': version.contract_date_start or employee._get_first_contract_date() or False,
            'l10n_ga_seniority_date': version._l10n_ga_seniority_start() or False,
            'l10n_ga_ssnid': version.ssnid or False,
            'l10n_ga_cnamgs_number': version.l10n_ga_cnamgs_number or False,
            'l10n_ga_nif': version.l10n_ga_nif or False,
            'l10n_ga_payment_mode': version.l10n_ga_payment_mode or False,
            'l10n_ga_bank_name': bank.bank_id.name or False,
            'l10n_ga_bank_account': bank.acc_number or False,
            'l10n_ga_company_nif': self.company_id.l10n_ga_nif or False,
            'l10n_ga_company_cnss': self.company_id.l10n_ga_cnss_number or False,
            'l10n_ga_company_cnamgs': self.company_id.l10n_ga_cnamgs_number or False,
        }

    def _l10n_ga_snapshot(self):
        """Valeurs à figer, calculées depuis les lignes du bulletin : ``(valeurs, PayResult, totaux)``."""
        self.ensure_one()
        totals = self._l10n_ga_line_totals()
        result = self._l10n_ga_result(self._l10n_ga_main_salary(), totals)
        params = self._l10n_ga_static()['params']
        values = {field_name: getattr(result, attr) for field_name, attr in FROZEN_RESULT_FIELDS.items()}
        values.update(
            l10n_ga_irpp_withheld=result.irpp + result.irpp_regularisation,
            l10n_ga_tax_parts_used=result.tax_parts,
            l10n_ga_marital_used=self.version_id.marital,
            l10n_ga_children_used=self.version_id.children,
            l10n_ga_cnss_ceiling_used=params.cnss_ceiling,
            l10n_ga_cnamgs_ceiling_used=params.cnamgs_ceiling,
            l10n_ga_rounding_carry=-totals.get('GA_ROUND', 0.0),
            l10n_ga_employee_contributions=result.cnss_employee + result.cnamgs_employee + result.fnh_employee,
            **self._l10n_ga_identity(),
            **self._l10n_ga_leave_counters(),
        )
        for ytd_field, month_field in YTD_FIELDS.items():
            values[ytd_field] = self._l10n_ga_ytd(month_field) + values[month_field]
        return values, result, totals

    def _l10n_ga_freeze(self):
        """Stocke les valeurs imprimées et déclarées du bulletin (F7), depuis ses lignes."""
        for slip in self.filtered(lambda s: s.l10n_ga_is_ga and s.state == 'draft' and s.line_ids):
            slip._l10n_ga_clear_cache()
            issues = slip._l10n_ga_blocking_issues()
            if issues:
                raise UserError('\n'.join(issues))
            values, result, totals = slip._l10n_ga_snapshot()
            slip._l10n_ga_check_lines(result, totals)
            slip.write({**values, 'l10n_ga_frozen_date': fields.Datetime.now()})
            slip._l10n_ga_freeze_lines(result)
            for line, (base, rate) in slip._l10n_ga_line_print_values(result).items():
                line.write({'l10n_ga_base': base or 0.0, 'l10n_ga_rate': rate or 0.0})
            slip._l10n_ga_clear_cache()

    # --- bulletin imprimé (F7, RG24) -------------------------------------------------------------

    def _l10n_ga_is_frozen(self):
        self.ensure_one()
        return self.state in VALIDATED_STATES and bool(self.l10n_ga_frozen_date)

    def _l10n_ga_leave_counters(self):
        """Congés payés au jour du bulletin (D-56) : base des 12 mois, jours acquis, pris, solde."""
        self.ensure_one()
        leave_type = self.env.ref(LEAVE_TYPE_XMLID, raise_if_not_found=False)
        acquired = taken = 0.0
        if leave_type:
            domain = [('employee_id', '=', self.employee_id.id), ('holiday_status_id', '=', leave_type.id)]
            allocations = (
                self.env['hr.leave.allocation']
                .sudo()
                .search([*domain, ('state', '=', 'validate'), ('date_from', '<=', self.date_to)])
            )
            leaves = (
                self.env['hr.leave']
                .sudo()
                .search([*domain, ('state', '=', 'validate'), ('request_date_from', '<=', self.date_to)])
            )
            acquired = sum(allocations.mapped('number_of_days'))
            taken = sum(leaves.mapped('number_of_days'))
        current = sum(self.line_ids.filtered(lambda line: line.salary_rule_id.l10n_ga_leave_base).mapped('total'))
        return {
            'l10n_ga_leave_base': self._l10n_ga_leave_reference_pay() + current,
            'l10n_ga_leave_acquired': acquired,
            'l10n_ga_leave_taken': taken,
            'l10n_ga_leave_balance': acquired - taken,
        }

    def _l10n_ga_line_print_values(self, result):
        """Base et taux imprimés par ligne (E3) : cotisations et impôts (noyau), heures supplémentaires."""
        self.ensure_one()
        bases = print_bases(result, self._l10n_ga_static()['params'])
        values = {}
        for line in self.line_ids:
            code = line.salary_rule_id.l10n_ga_core_value
            if code in bases:
                values[line] = bases[code]
            elif code and code.startswith(OVERTIME_PREFIX):
                values[line] = (self._l10n_ga_overtime_hours(code.removeprefix(OVERTIME_PREFIX)), None)
            elif line.code == BASIC_CODE and self._l10n_ga_uses_reference_hours():
                values[line] = (self._l10n_ga_basic_hours(), self._l10n_ga_hourly_rate())  # figés (F7)
        return values

    # --- bulletin imprimé (F7, RG24, plan 2.7 b) ---------------------------------------------------

    def _l10n_ga_is_frozen(self):
        self.ensure_one()
        return self.state in VALIDATED_STATES and bool(self.l10n_ga_frozen_date)

    def _l10n_ga_report_field_names(self):
        return [
            *self._l10n_ga_identity(),
            *FROZEN_RESULT_FIELDS,
            *YTD_FIELDS,
            'l10n_ga_irpp_withheld',
            'l10n_ga_tax_parts_used',
            'l10n_ga_marital_used',
            'l10n_ga_children_used',
            'l10n_ga_cnss_ceiling_used',
            'l10n_ga_cnamgs_ceiling_used',
            'l10n_ga_rounding_carry',
            'l10n_ga_employee_contributions',
            'l10n_ga_leave_base',
            'l10n_ga_leave_acquired',
            'l10n_ga_leave_taken',
            'l10n_ga_leave_balance',
        ]

    def _l10n_ga_report_data(self):
        """Valeurs imprimées : champs figés d'un bulletin validé, sinon calcul du jour (brouillon).

        ``line_values`` : ligne → (base, taux) figés (validé) ou calculés (brouillon).
        """
        self.ensure_one()
        names = self._l10n_ga_report_field_names()
        if self._l10n_ga_is_frozen():
            data = {name: self[name] for name in names}
            data['line_values'] = {line: (line.l10n_ga_base, line.l10n_ga_rate) for line in self.line_ids}
            data['edited'] = self.l10n_ga_frozen_date.date()
        elif self.line_ids:
            self._l10n_ga_clear_cache()
            data, result, _totals = self._l10n_ga_snapshot()
            data['line_values'] = self._l10n_ga_line_print_values(result)
            self._l10n_ga_clear_cache()
            data['edited'] = fields.Date.context_today(self)
        else:
            data = dict.fromkeys(names, False) | self._l10n_ga_identity()
            data['line_values'] = {}
            data['edited'] = fields.Date.context_today(self)
        data['frozen'] = self._l10n_ga_is_frozen()
        data['payment_mode_label'] = dict(PAYMENT_MODE_SELECTION).get(data['l10n_ga_payment_mode'], '')
        marital = dict(self.env['hr.version']._fields['marital']._description_selection(self.env))
        data['marital_label'] = marital.get(data['l10n_ga_marital_used'], data['l10n_ga_marital_used'] or '')
        basic = self.line_ids.filtered(lambda line: line.code == BASIC_CODE)[:1]
        # « Horaires » : quantité (figée) de la ligne de base (FIX 01), pas le total du calendrier.
        data['month_hours'] = data['line_values'].get(basic, (None, None))[0] if basic else None
        if not data['month_hours']:  # bulletin figé avant le FIX 01 : heures du calendrier
            data['month_hours'] = sum(self._l10n_ga_month_lines().mapped('number_of_hours'))
        totals = self._l10n_ga_line_totals()
        data['net_pay'] = totals.get('GA_NET_PAY', totals.get('NET', 0.0))
        return data

    def _l10n_ga_month_lines(self):
        """Prestations du mois hors heures supplémentaires (horaires du bulletin)."""
        return self.worked_days_line_ids.filtered(lambda wd: not wd.work_entry_type_id.is_extra_hours)

    def _l10n_ga_is_employer_line(self, line):
        category = line.category_id
        while category:
            if category.code == 'GA_EMPLOYER':
                return True
            category = category.parent_id
        return False

    @staticmethod
    def _l10n_ga_row(code, name, amount=None, *, base=None, rate=None, style='line', **values):
        return {
            'code': code,
            'name': name,
            'base': base,
            'rate': rate,
            'amount': amount,
            'employer_rate': values.get('employer_rate'),
            'employer_amount': values.get('employer_amount'),
            'base_digits': values.get('base_digits', 0),
            'style': style,
        }

    def _l10n_ga_group_row(self, code, lines, line_values):
        """Une ligne par code imprimé : part salariale et parts patronales d'un organisme réunies (D-54)."""
        employee = [line for line in lines if not self._l10n_ga_is_employer_line(line)]
        employer = [line for line in lines if self._l10n_ga_is_employer_line(line)]
        first = (employee or employer)[0]
        name = first.salary_rule_id.l10n_ga_print_name or first.name
        base, rate = line_values.get(first, (None, None))
        employer_values = [line_values.get(line, (None, None)) for line in employer]
        employer_rate = None
        if employer_values and all(r for _b, r in employer_values) and len({b for b, _r in employer_values}) == 1:
            employer_rate = sum(r for _b, r in employer_values)
        if not employee:
            rate = None  # base commune affichée, taux patronal dans sa colonne
        overtime = (first.salary_rule_id.l10n_ga_core_value or '').startswith(OVERTIME_PREFIX)
        return self._l10n_ga_row(
            code,
            name,
            amount=sum(line.total for line in employee) if employee else None,
            base=base or None,
            rate=rate or None,
            employer_rate=employer_rate,
            employer_amount=sum(line.total for line in employer) if employer else None,
            base_digits=2 if overtime else 0,
        )

    def _l10n_ga_basic_rows(self, row, data):
        """Salaire de base en deux lignes (E4, affichage) : mois de référence au taux horaire unique, puis
        heures non payées (FIX 01). Base et taux lus sur la ligne figée."""
        wage = data.get('l10n_ga_wage') or 0.0
        quantity, rate = row['base'], row['rate']
        if self.wage_type == 'hourly' or not wage or not rate:
            return [row]
        reference = self._l10n_ga_reference_hours()  # paramètre daté à la date du bulletin
        basic = row['amount'] or 0.0
        rows = [dict(row, amount=wage, base=reference, rate=rate, base_digits=2)]
        if round_fcfa(basic) != round_fcfa(wage):
            rows.append(
                self._l10n_ga_row(
                    str(layout.ABSENCE),
                    self.env._('Absences et congés non payés au salaire de base'),
                    amount=basic - wage,
                    base=(reference - (quantity or 0.0)) or None,
                    rate=-rate,
                    base_digits=2,
                )
            )
        return rows

    def _l10n_ga_report_rows(self, data=None):
        """Lignes du bulletin imprimé dans l'ordre du modèle (plan 2.7 b), totaux compris (D-55)."""
        self.ensure_one()
        data = data or self._l10n_ga_report_data()
        groups = defaultdict(list)
        for line in self.line_ids.sorted(lambda li: (li.sequence, li.id)):
            code = line.salary_rule_id.l10n_ga_print_code
            if code and line.total:
                groups[code].append(line)
        rows = []
        sums = defaultdict(float)
        for code, lines in groups.items():
            row = self._l10n_ga_group_row(code, lines, data['line_values'])
            section = layout.section(code)
            sums[section] += row['amount'] or 0.0
            if section == layout.CONTRIBUTIONS:
                sums['employer'] += row['employer_amount'] or 0.0
            if lines[0].code == 'BASIC':
                rows += self._l10n_ga_basic_rows(row, data)
            else:
                rows.append(row)
        pay_codes = {
            line.code
            for lines in groups.values()
            for line in lines
            if layout.section(line.salary_rule_id.l10n_ga_print_code) == layout.PAY
        }
        if not pay_codes & {'GA_ROUND_PREV', 'GA_ROUND'}:
            rows = [row for row in rows if not (groups.get(row['code']) and groups[row['code']][0].code == 'NET')]
        total = self._l10n_ga_row
        rows.append(total(str(layout.TOTAL_GROSS), self.env._('TOTAL BRUT'), sums[layout.GAINS], style='total'))
        if sums[layout.CONTRIBUTIONS] or sums['employer']:
            rows.append(
                total(
                    str(layout.TOTAL_CONTRIBUTIONS),
                    self.env._('TOTAL COTISATIONS'),
                    sums[layout.CONTRIBUTIONS],
                    employer_amount=sums['employer'],
                    style='total',
                )
            )
        if sums[layout.BENEFITS]:
            rows.append(
                total(
                    str(layout.TOTAL_BENEFITS),
                    self.env._('Total avantages en nature'),
                    sums[layout.BENEFITS],
                    style='total',
                )
            )
        if data.get('l10n_ga_tcs_base'):
            rows.append(
                total(
                    str(layout.TCS_BASE), self.env._('Base TCS mensuelle'), base=data['l10n_ga_tcs_base'], style='info'
                )
            )
        rows.append(
            total(
                str(layout.TOTAL_GAINS),
                self.env._('TOTAL GAINS'),
                sums[layout.GAINS] + sums[layout.ALLOWANCES],
                style='total',
            )
        )
        deductions = sums[layout.CONTRIBUTIONS] + sums[layout.TAXES] + sums[layout.DEDUCTIONS]
        rows.append(total(str(layout.TOTAL_DEDUCTIONS), self.env._('TOTAL RETENUES'), deductions, style='total'))
        for row in rows:
            if row['code'] in groups and groups[row['code']][0].code == 'GA_NET_PAY':
                row['style'] = 'total'
        return sorted(rows, key=lambda row: int(row['code']))

    @staticmethod
    def _l10n_ga_fmt(amount, digits=0):
        """Nombre imprimé : séparateur de milliers insécable, virgule décimale (vide si ``None``)."""
        if amount is None or amount is False:
            return ''
        value = round_fcfa(amount) if not digits else round(amount, digits)
        text = f'{value:,.{digits}f}'
        return text.replace(',', '\u202f').replace('.', ',')

    @staticmethod
    def _l10n_ga_fmt_rate(rate):
        """Taux imprimé : décimales inutiles retirées (2,5 ; 16 ; 4,1)."""
        if not rate:
            return ''
        return f'{rate:.3f}'.rstrip('0').rstrip('.').replace('.', ',')

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
