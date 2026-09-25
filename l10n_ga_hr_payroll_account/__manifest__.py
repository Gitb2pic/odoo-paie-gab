{
    'name': 'Gabon - Paie avec comptabilité',
    'version': '19.0.1.0.0',
    'summary': 'Imputation SYSCOHADA des bulletins gabonais : comptes par société, journal, contrôles, soldes',
    'countries': ['ga'],
    'category': 'Human Resources/Payroll',
    'author': 'OMIAS Leadership Group',
    'maintainer': 'MPAMI MPAMI Nathan Mael Alex',
    # l10n_ga : plan « ga » dont les comptes pcg_* sont liés aux règles (décision D-63)
    'depends': ['l10n_ga_hr_payroll', 'hr_payroll_account', 'l10n_ga'],
    'data': [
        'data/hr_salary_rule_data.xml',
        'data/account_chart_template_data.xml',
        'data/ir_actions_server_data.xml',
    ],
    'auto_install': True,
    'license': 'OPL-1',
}
