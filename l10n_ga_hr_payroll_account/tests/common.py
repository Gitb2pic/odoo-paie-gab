"""Sociétés au plan « ga » et lots de paie validés (aucune donnée de démo)."""

from collections import defaultdict
from datetime import date

from odoo.addons.l10n_ga_hr_payroll.tests.common import GaPayrollCase

from ..models.account_chart_template import RULE_ACCOUNTS

AUG = (date(2026, 8, 1), date(2026, 8, 31))
SEPT = (date(2026, 9, 1), date(2026, 9, 30))


class GaPayrollAccountCase(GaPayrollCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._load_chart(cls.company)

    @classmethod
    def _load_chart(cls, company):
        cls.env['account.chart.template'].try_loading('ga', company, install_demo=False)

    @classmethod
    def _new_company(cls, name):
        company = cls.env['res.company'].create(
            {'name': name, 'country_id': cls.env.ref('base.ga').id, 'currency_id': cls.env.ref('base.XAF').id}
        )
        cls.env.user.company_ids |= company
        return company

    @classmethod
    def _account(cls, code, company=None):
        return cls.env['account.chart.template'].with_company(company or cls.company).ref(f'pcg_{code}')

    @classmethod
    def _complete(cls, name, mode='transfer', company=None, wage=400_000, start=date(2020, 1, 1)):
        """Salarié sans anomalie de contrôle (n° CNSS, NIF, compte bancaire)."""
        company = company or cls.company
        employee = cls._employee(name, wage, start=start, company_id=company.id, ssnid='CNSS-1', l10n_ga_nif='NIF-1')
        bank = cls.env['res.partner.bank'].create(
            {'acc_number': f'GA-{employee.id}', 'partner_id': employee.work_contact_id.id, 'allow_out_payment': True}
        )
        employee.bank_account_ids = [(4, bank.id)]
        employee.version_id.l10n_ga_payment_mode = mode
        return employee

    @classmethod
    def _run(cls, employees, company=None, period=SEPT, validate=True):
        company = company or cls.company
        run = cls.env['hr.payslip.run'].create(
            {
                'name': f'Lot {company.name}',
                'company_id': company.id,
                'date_start': period[0],
                'date_end': period[1],
                'structure_id': cls.structure.id,
            }
        )
        for employee in employees:
            cls.env['hr.payslip'].create(
                {
                    'name': f'{employee.name} {period[0]:%m/%Y}',
                    'employee_id': employee.id,
                    'date_from': period[0],
                    'date_to': period[1],
                    'payslip_run_id': run.id,
                }
            )
        run.action_confirm()
        if validate:
            run.action_validate()
        return run

    @staticmethod
    def _balances(moves):
        """Solde (débit − crédit) par compte."""
        balances = defaultdict(float)
        for line in moves.line_ids:
            balances[line.account_id] += line.debit - line.credit
        return balances

    @classmethod
    def _expected_balances(cls, slips):
        """Soldes attendus d'après la table d'imputation et les lignes des bulletins."""
        balances = defaultdict(float)
        for line in slips.line_ids:
            for key, template_xmlid in RULE_ACCOUNTS.get(line.code, {}).items():
                account = cls.env['account.chart.template'].with_company(line.slip_id.company_id).ref(template_xmlid)
                balances[account] += line.total if key == 'debit' else -line.total
        return {account: balance for account, balance in balances.items() if balance}
