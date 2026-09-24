"""Adaptateur du bulletin Odoo vers le noyau fiscal (patron 2, anti-corruption) et bulletin figé (F7, F16).

Les règles fiscales tiennent en une ligne : ``payslip._l10n_ga_compute(<valeur>, categories, result_rules)``.
Le ``PayResult`` est calculé une fois par bulletin et par jeu de faits (cache dans ``cr.cache``),
purgé en tête de chaque calcul. À la validation, les valeurs imprimées et déclarées sont figées
depuis les lignes du bulletin : un bulletin validé ne relit plus jamais les paramètres.
"""

from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..lib.ga_fiscal_core.benefits import benefit_code
from ..lib.ga_fiscal_core.engine import PayslipFacts, compute
from ..lib.ga_fiscal_core.exemptions import GainLine
from ..lib.ga_fiscal_core.rounding import round_fcfa
from ..lib.ga_fiscal_core.treatment import NONE, social_group, tax_group

GA_CODE = 'GA'
AIK_CATEGORY = 'GA_AIK'
BASIC_CATEGORY = 'BASIC'
BENEFIT_PREFIX = 'benefit:'
CACHE_KEY = 'l10n_ga_hr_payroll.payslip'
VALIDATED_STATES = ('validated', 'paid')  # sprint 0 point 3 : pas d'état « done » en 19

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
    l10n_ga_is_ga = fields.Boolean(compute='_compute_l10n_ga_is_ga')

    @api.depends('date_to')
    def _compute_l10n_ga_payment_date(self):
        for slip in self:
            slip.l10n_ga_payment_date = slip.date_to

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

    def _l10n_ga_ytd(self, field_name):
        """Cumul d'un champ figé sur les bulletins validés antérieurs de l'année civile."""
        self.ensure_one()
        [(total,)] = self.env['hr.payslip']._read_group(self._l10n_ga_ytd_domain(), aggregates=[f'{field_name}:sum'])
        return total or 0.0

    def _l10n_ga_regularize(self):
        """Régularisation annuelle de l'IRPP : dernier bulletin de l'année ou départ dans la période."""
        self.ensure_one()
        if (self.date_to + timedelta(days=1)).year != self.date_to.year:
            return True
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
                'results': {},
            }
        return entry

    def _l10n_ga_clear_cache(self):
        cache = self.env.cr.cache.get(CACHE_KEY)
        if cache:
            for slip_id in self.ids:
                cache.pop(slip_id, None)

    def _l10n_ga_gain_lines(self, totals):
        """Une ``GainLine`` par rubrique de gain en espèces de la structure (``totals`` : code → total)."""
        self.ensure_one()
        lines = []
        for rule in self.struct_id.rule_ids.sorted(lambda r: (r.sequence, r.id)):
            if rule.l10n_ga_social_base in (False, NONE) or rule.category_id.code == AIK_CATEGORY:
                continue
            amount = totals.get(rule.code, 0.0)
            if not amount:
                continue
            lines.append(
                GainLine(
                    rule.code,
                    amount,
                    social_group(rule.l10n_ga_social_base, rule.l10n_ga_social_cap_group or None),
                    tax_group(rule.l10n_ga_tax_base, rule.l10n_ga_tax_cap_group or None),
                )
            )
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

    def _l10n_ga_compute(self, code, categories, result_rules):
        """Point d'entrée des règles salariales (une ligne) : montant ``code`` du ``PayResult``."""
        self.ensure_one()
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
            expected = rule._l10n_ga_sign() * self._l10n_ga_value(result, rule.l10n_ga_core_value)
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
        for exemption in result.lines:
            code = codes.get(exemption.code, exemption.code)
            lines = self.line_ids.filtered(lambda line, code=code: line.code == code)
            total = sum(lines.mapped('total'))
            remaining = {
                'l10n_ga_social_excluded': exemption.social_excluded,
                'l10n_ga_tax_exempt': exemption.tax_exempt,
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
            )
            for ytd_field, month_field in YTD_FIELDS.items():
                values[ytd_field] = slip._l10n_ga_ytd(month_field) + values[month_field]
            slip.write(values)
            slip._l10n_ga_freeze_lines(result)
            slip._l10n_ga_clear_cache()

    def action_payslip_done(self):
        # Avant super() : bulletin encore en brouillon, lignes calculées (sprint 0 point 13).
        self._l10n_ga_freeze()
        return super().action_payslip_done()
