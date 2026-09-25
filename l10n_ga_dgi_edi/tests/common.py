"""Fabrique des tests du moteur de déclarations : type d'essai, salariés, bulletins validés, utilisateurs."""

from datetime import date

from odoo.addons.l10n_ga_hr_payroll.tests.common import GaPayrollCase
from odoo.fields import Command

SEPT = (date(2026, 9, 1), date(2026, 9, 30))
F16_INPUTS = {'GA_TRANSP': 35_000, 'GA_RESP': 105_000}
# Cas F16 (fichier 08) : IRPP 23 195, TCS 13 058, CNSS salariale 27 750, FNH 16 650, CFP 2 775.
F16_IRPP, F16_TCS, F16_CNSS, F16_FNH = 23_195, 13_058, 27_750, 16_650
F16_CNAMGS, F16_CFP, F16_SOCIAL_BASE = 11_100, 2_775, 555_000


class FakeGenerator:
    """Générateur factice (interface du registre) : valeurs imposées par le test."""

    def __init__(self, values=None, details=(), issues=(), parameters=()):
        self.values = values or {}
        self.details = list(details)
        self.issues = list(issues)
        self.parameters = list(parameters)
        self.calls = []

    def _collect(self, declaration):
        self.calls.append(('collect', declaration.id))
        return {'facts': True}

    def _fill(self, declaration, facts):
        self.calls.append(('fill', facts))
        return dict(self.values)

    def _details(self, declaration, facts):
        return list(self.details)

    def _checks(self, declaration, facts):
        return list(self.issues)

    def _required_parameters(self, declaration):
        return list(self.parameters)

    def _requires_cnss_number(self, declaration):
        return True

    def _detail_columns(self, declaration):
        return []

    def _applies(self, company):
        return True

    def _render_workbook(self, declaration):
        return None

    def _fill_template(self, declaration, renderer):
        return None


class GaDeclarationCase(GaPayrollCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write(
            {
                'l10n_ga_nif': 'NIF-TEST',
                'l10n_ga_cnss_number': 'CNSS-EMP',
                'l10n_ga_tax_center': 'LBV-01',
                'city': 'Libreville',
                'street': 'BP 1234',
            }
        )
        cls.decl_type = cls._declaration_type('T_PAY')
        cls.payroll_user = cls._user('ga_decl_payroll', 'hr_payroll.group_hr_payroll_user')
        cls.declarant = cls._user('ga_decl_declarant', 'l10n_ga_dgi_edi.group_l10n_ga_declarant')
        cls.manager = cls._user('ga_decl_manager', 'l10n_ga_dgi_edi.group_l10n_ga_declaration_manager')

    @classmethod
    def _user(cls, login, group_xmlid, company=None):
        company = company or cls.company
        return cls.env['res.users'].create(
            {
                'name': login,
                'login': login,
                'company_id': company.id,
                'company_ids': [Command.set(company.ids)],
                'group_ids': [Command.set(cls.env.ref(group_xmlid).ids)],
            }
        )

    @classmethod
    def _declaration_type(cls, code, auto_create=False, **values):
        boxes = [
            ('HDR_NIF', 'NIF', 'text', {'auto_value': 'company_nif', 'cell_ref': 'B2'}),
            ('HDR_MONTH', 'Mois', 'number', {'auto_value': 'period_month', 'cell_ref': 'B3'}),
            ('B_IRPP', 'IRPP', 'amount', {'source_codes': '-GA_IRPP, -GA_IRPP_REGUL', 'is_total': True}),
            ('B_TCS', 'TCS', 'amount', {'source_codes': '-GA_TCS', 'is_total': True, 'cell_ref': 'C11'}),
            ('B_FNH', 'FNH', 'amount', {'source_codes': 'GA_FNH', 'is_total': True, 'cell_ref': 'C12'}),
            ('B_CNSS', 'CNSS salariale', 'amount', {'source_codes': '-GA_CNSS_SAL'}),
        ]
        return cls.env['l10n_ga.declaration.type'].create(
            {
                'code': code,
                'name': f'Imprimé {code}',
                'generator_key': 'payslip',
                'auto_create': auto_create,
                'box_ids': [
                    Command.create({'code': box, 'name': name, 'value_kind': kind, 'sequence': index, **extra})
                    for index, (box, name, kind, extra) in enumerate(boxes)
                ],
                **values,
            }
        )

    @classmethod
    def _f16_employee(cls, name='F16', **values):
        values.setdefault('ssnid', f'CNSS-{name}')
        values.setdefault('l10n_ga_cnamgs_number', f'CNAMGS-{name}')
        values.setdefault('l10n_ga_nif', f'NIF-{name}')
        return cls._employee(name, 450_000, l10n_ga_transport_trips='2', **values)

    @classmethod
    def _f16_slip(cls, employee=None, period=SEPT, validate=True, payment_date=None):
        employee = employee or cls._f16_employee()
        slip = cls._payslip(employee, *period, inputs=F16_INPUTS)
        if payment_date:
            slip.l10n_ga_payment_date = payment_date
        if validate:
            slip.action_payslip_done()
        return slip

    @classmethod
    def _declaration(cls, decl_type=None, period=SEPT, company=None, **values):
        return cls.env['l10n_ga.declaration'].create(
            {
                'company_id': (company or cls.company).id,
                'type_id': (decl_type or cls.decl_type).id,
                'date_from': period[0],
                'date_to': period[1],
                **values,
            }
        )

    @classmethod
    def _type(cls, code):
        return cls.env.ref(f'l10n_ga_dgi_edi.declaration_type_{code.lower()}')

    @classmethod
    def _find(cls, decl_type, period=SEPT, company=None):
        return cls.env['l10n_ga.declaration'].search(
            [
                ('company_id', '=', (company or cls.company).id),
                ('type_id', '=', decl_type.id),
                ('date_from', '=', period[0]),
                ('date_to', '=', period[1]),
                ('rectified_id', '=', False),
                ('state', '!=', 'cancel'),
            ]
        )

    @staticmethod
    def _values(declaration):
        return {line.code: line._value() for line in declaration.line_ids}

    @staticmethod
    def _box(declaration, code):
        return declaration.line_ids.filtered(lambda line: line.code == code)
