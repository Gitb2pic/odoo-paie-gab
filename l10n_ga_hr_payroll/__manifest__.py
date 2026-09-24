{
    'name': 'Gabon - Paie',
    'version': '19.0.1.0.0',
    'summary': 'Paie gabonaise : CNSS, CNAMGS, TCS, IRPP, FNH, CFP, rubriques et absences',
    'countries': ['ga'],
    'category': 'Human Resources/Payroll',
    # hr_work_entry_holidays : types d'absence reliés aux prestations (F4, décision D-15)
    'depends': ['hr_payroll', 'hr_work_entry_holidays', 'l10n_ga'],
    'data': [
        'security/ir.model.access.csv',
        'security/l10n_ga_hr_payroll_security.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_salary_rule_data.xml',
        'data/hr_rule_parameters_data.xml',
        'data/hr_work_entry_type_data.xml',
        'data/hr_leave_type_data.xml',
        'data/ir_sequence_data.xml',
    ],
    'external_dependencies': {'python': ['openpyxl', 'xlsxwriter']},
    'license': 'OPL-1',
}
