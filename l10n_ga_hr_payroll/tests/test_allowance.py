from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import GaPayrollCase

SEPT = (date(2026, 9, 1), date(2026, 9, 30))
OCT = (date(2026, 10, 1), date(2026, 10, 31))


@tagged('post_install', '-at_install')
class TestAllowance(GaPayrollCase):
    """F15, RG28, ADR-16 : indemnités récurrentes = ajustements de salaire Gabon datés."""

    def _allowance(self, employee, code, amount=30_000, start=date(2026, 1, 1), end=False, **values):
        return self.env['hr.salary.attachment'].create(
            {
                'employee_ids': [(6, 0, employee.ids)],
                'other_input_type_id': self._input_type(code).id,
                'monthly_amount': amount,
                'duration_type': 'unlimited',
                'date_start': start,
                'date_end': end,
                **values,
            }
        )

    @staticmethod
    def _inputs(slip, code):
        return slip.input_line_ids.filtered(lambda line: line.code == code)

    # --- RG28 -------------------------------------------------------------------------------------

    def test_overlap_refused(self):
        employee = self._employee('Chevauchement', 400_000)
        first = self._allowance(employee, 'GA_TRANSP')
        with self.assertRaises(ValidationError) as error:
            self._allowance(employee, 'GA_TRANSP', start=date(2026, 6, 1))
        self.assertIn('chevauche', str(error.exception))
        first.date_end = date(2026, 5, 31)
        self._allowance(employee, 'GA_TRANSP', start=date(2026, 6, 1))  # revalorisation datée
        with self.assertRaises(ValidationError) as error:
            self._allowance(employee, 'GA_TRANSP', start=date(2025, 1, 1), end=date(2026, 2, 1))
        self.assertIn('chevauche', str(error.exception))
        self._allowance(employee, 'GA_RESP')  # autre type : accepté

    def test_overlap_ignores_closed_and_deductions(self):
        employee = self._employee('Clôturée', 400_000)
        self._allowance(employee, 'GA_TRANSP').action_close()
        self._allowance(employee, 'GA_TRANSP')
        self._allowance(employee, 'GA_ASSIGN', amount=5_000)
        self._allowance(employee, 'GA_ASSIGN', amount=5_000)  # retenue : comportement standard

    # --- montant sur le bulletin -----------------------------------------------------------------

    def test_one_marked_input_per_allowance(self):
        employee = self._employee('Indemnité fixe', 400_000)
        allowance = self._allowance(employee, 'GA_TRANSP')
        slip = self._payslip(employee, *SEPT)
        inputs = self._inputs(slip, 'GA_TRANSP')
        self.assertEqual((inputs.amount, inputs.l10n_ga_allowance_id), (30_000, allowance))
        self.assertEqual(self._totals(slip)['GA_TRANSP'], 30_000)

    def test_prorata_start_of_month(self):
        employee = self._employee('Début 16', 400_000)
        self._allowance(employee, 'GA_TRANSP', start=date(2026, 9, 16))
        self.assertEqual(self._inputs(self._payslip(employee, *SEPT), 'GA_TRANSP').amount, 15_000)

    def test_prorata_end_of_month_and_revaluation(self):
        employee = self._employee('Revalorisation', 400_000)
        self._allowance(employee, 'GA_TRANSP', end=date(2026, 9, 15))
        self._allowance(employee, 'GA_TRANSP', amount=60_000, start=date(2026, 9, 16))
        slip = self._payslip(employee, *SEPT)
        self.assertEqual(sorted(self._inputs(slip, 'GA_TRANSP').mapped('amount')), [15_000, 30_000])
        self.assertEqual(self._totals(slip)['GA_TRANSP'], 45_000)
        self.assertEqual(self._inputs(self._payslip(employee, *OCT), 'GA_TRANSP').amount, 60_000)

    def test_manual_input_replaces_automatic(self):
        employee = self._employee('Saisie manuelle', 400_000)
        self._allowance(employee, 'GA_TRANSP')
        slip = self._payslip(employee, *SEPT)
        slip.write({'input_line_ids': [(0, 0, {'input_type_id': self._input_type('GA_TRANSP').id, 'amount': 12_000})]})
        slip.compute_sheet()
        inputs = self._inputs(slip, 'GA_TRANSP')
        self.assertEqual(inputs.mapped('amount'), [12_000])
        self.assertFalse(inputs.l10n_ga_allowance_id)
        self.assertEqual(self._totals(slip)['GA_TRANSP'], 12_000)

    def test_wage_percent_follows_version(self):
        employee = self._employee('Pourcentage', 400_000)
        allowance = self._allowance(employee, 'GA_SURSAL', amount=0, l10n_ga_mode='wage_percent', l10n_ga_rate=10)
        # le montant saisi est ignoré en mode calculé : montant indicatif = 10 % du salaire
        self.assertEqual(allowance.monthly_amount, 40_000)
        self.assertEqual(self._inputs(self._payslip(employee, *SEPT), 'GA_SURSAL').amount, 40_000)
        employee.create_version({'date_version': date(2026, 10, 1), 'wage': 500_000})
        self.assertEqual(self._inputs(self._payslip(employee, *OCT), 'GA_SURSAL').amount, 50_000)

    def test_quantity_times_rate(self):
        employee = self._employee('Quantité', 400_000)
        self._allowance(
            employee, 'GA_RISQUE', amount=0, l10n_ga_mode='quantity_rate', l10n_ga_quantity=10, l10n_ga_rate=2_000
        )
        self.assertEqual(self._inputs(self._payslip(employee, *SEPT), 'GA_RISQUE').amount, 20_000)

    def test_deduction_attachment_keeps_standard_behaviour(self):
        employee = self._employee('Cession', 400_000)
        self._allowance(employee, 'GA_ASSIGN', amount=5_000)
        inputs = self._inputs(self._payslip(employee, *SEPT), 'GA_ASSIGN')
        self.assertEqual(inputs.amount, 5_000)
        self.assertFalse(inputs.l10n_ga_allowance_id)

    # --- forcée imposable (D-36) -----------------------------------------------------------------

    def test_forced_taxable_requires_reason(self):
        employee = self._employee('Sans motif', 400_000)
        with self.assertRaises(ValidationError) as error:
            self._allowance(employee, 'GA_RESP', l10n_ga_forced_taxable=True)
        self.assertIn('motivée', str(error.exception))

    def test_forced_taxable_loses_exemption(self):
        normal = self._employee('Exonérée', 400_000)
        forced = self._employee('Forcée', 400_000)
        self._allowance(normal, 'GA_RESP', amount=50_000)
        self._allowance(
            forced, 'GA_RESP', amount=50_000, l10n_ga_forced_taxable=True, l10n_ga_forced_reason='Non justifiée'
        )
        slip_normal = self._validated(normal, *SEPT)
        slip_forced = self._validated(forced, *SEPT)
        self.assertTrue(self._inputs(slip_forced, 'GA_RESP').l10n_ga_forced_taxable)
        self.assertEqual(self._line(slip_normal, 'GA_RESP').l10n_ga_tax_exempt, 50_000)
        self.assertEqual(self._line(slip_forced, 'GA_RESP').l10n_ga_tax_exempt, 0)
        self.assertEqual(slip_forced.l10n_ga_taxable_gross - slip_normal.l10n_ga_taxable_gross, 50_000)
        self.assertGreater(-self._totals(slip_forced)['GA_IRPP'], -self._totals(slip_normal)['GA_IRPP'])

    def test_forced_taxable_on_part_of_the_month(self):
        employee = self._employee('Forcée partielle', 400_000)
        self._allowance(employee, 'GA_RESP', amount=60_000, end=date(2026, 9, 15))
        self._allowance(
            employee,
            'GA_RESP',
            amount=60_000,
            start=date(2026, 9, 16),
            l10n_ga_forced_taxable=True,
            l10n_ga_forced_reason='Non justifiée',
        )
        slip = self._validated(employee, *SEPT)
        lines = self._line(slip, 'GA_RESP')  # une ligne par entrée
        self.assertEqual(len(lines), 2)
        self.assertEqual(sum(lines.mapped('total')), 60_000)
        self.assertEqual(sum(lines.mapped('l10n_ga_tax_exempt')), 30_000)
        self.assertEqual(slip.l10n_ga_tax_exempt, 30_000)

    # --- ADR-16 : pas de paiement enregistré, bouton intelligent ---------------------------------

    def test_record_payment_without_effect(self):
        employee = self._employee('Payée', 400_000)
        allowance = self._allowance(employee, 'GA_TRANSP', end=date(2026, 9, 30))
        slip = self._validated(employee, *SEPT)
        slip.action_payslip_paid()
        self.assertEqual((allowance.state, allowance.paid_amount), ('open', 0))

    def test_employee_smart_button(self):
        employee = self._employee('Bouton', 400_000)
        allowance = self._allowance(employee, 'GA_TRANSP')
        self._allowance(employee, 'GA_ASSIGN', amount=5_000)
        self.assertEqual(employee.l10n_ga_allowance_count, 1)
        action = employee.action_l10n_ga_allowances()
        self.assertEqual(self.env['hr.salary.attachment'].search(action['domain']), allowance)
