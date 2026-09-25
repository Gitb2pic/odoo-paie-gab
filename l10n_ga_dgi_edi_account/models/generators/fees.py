"""Annexes annuelles de la DAS : ID23 (honoraires versés au Gabon), ID24 (hors du Gabon), ID26
(prestataires non assujettis à la TVA) — base 06 §3.2, art. 182 et 189 CGI.

Sommes versées dans l'année (D-97) = part HT des factures réglée par les paiements validés de l'année
(``payments.settled_ht_by_partner``, avoir en négatif). Retenues : lignes de retenue des paiements de
l'année, comme l'ID18 / l'ID27. Classeur neuf mis en forme : les
gabarits .xlsm de la V1 sont absents (D-87, D-99).
"""

from odoo import fields, models
from odoo.addons.l10n_ga_dgi_edi.models.declaration_generator import BLOCKING, WARNING
from odoo.addons.l10n_ga_dgi_edi.renderers.xlsx_builder import XlsxDeclarationBuilder
from odoo.tools import float_compare, float_round

from ..res_partner import DAS_FEE_CATEGORIES, FEE_CATEGORIES
from .payments import settled_ht_by_partner, withholding_by_partner
from .withholding import WITHHELD

PAID = 'TOTAL_PAID'


class L10nGaDeclarationGeneratorFees(models.AbstractModel):
    _name = 'l10n_ga.declaration.generator.fees'
    _inherit = 'l10n_ga.declaration.generator.base'
    _description = 'Sommes versées aux tiers dans l’année (base commune ID23 / ID24 / ID26)'

    _kind = None  # retenue lue (ID24 : 20 % ; ID26 : 9,5 % ; ID23 : aucune)
    _monthly_type = None  # imprimé mensuel dont la DAS reprend les retenues (ID27 / ID18)
    _sections = ()  # [(code de section, case des sommes versées, libellé)]
    _nif_required = True

    def _requires_cnss_number(self, declaration):
        return False

    def _partner_domain(self, declaration):
        raise NotImplementedError  # interface abstraite : bénéficiaires de l'annexe

    def _section(self, declaration, partner):
        return self._sections[0][0]

    # --- collecte -----------------------------------------------------------------------------

    def _withheld(self, declaration):
        if not self._kind:
            return {}
        taxes = self.env['account.tax']._l10n_ga_withholding_taxes(declaration.company_id, self._kind)
        by_partner = withholding_by_partner(
            self.env, declaration.company_id, declaration.date_from, declaration.date_to, taxes
        )
        return {partner: (item['withheld'], item['lines']) for partner, item in by_partner.items()}

    def _collect(self, declaration):
        partners = self.env['res.partner'].search(self._partner_domain(declaration))
        withheld = self._withheld(declaration)
        partners |= self.env['res.partner'].concat(*withheld)  # retenus dans l'année, même non classés
        paid = settled_ht_by_partner(
            self.env, declaration.company_id, declaration.date_from, declaration.date_to, partners
        )
        return {'paid': {partner: tuple(item) for partner, item in paid.items()}, 'withheld': withheld}

    def _details(self, declaration, facts):
        categories = dict(FEE_CATEGORIES)
        boxes = {code: box for code, box, _label in self._sections}
        details = []
        partners = set(facts['paid']) | set(facts['withheld'])
        for partner in sorted(partners, key=lambda p: (p.name or '', p.id)):
            paid, paid_lines = facts['paid'].get(partner, (0.0, self.env['account.move.line']))
            withheld, withheld_lines = facts['withheld'].get(partner, (0.0, self.env['account.move.line']))
            section = self._section(declaration, partner)
            payload = {
                'section': section,
                'name': partner.name or '',
                'nif': partner.vat or '',
                'profession': categories.get(partner.l10n_ga_fee_category, ''),
                'address': ', '.join(filter(None, [partner.street, partner.city, partner.country_id.name])),
                'paid': float_round(paid, precision_digits=0),
                'withheld': float_round(withheld, precision_digits=0),
            }
            details.append(
                {
                    'box_code': boxes[section],
                    'partner_id': partner.id,
                    'label': payload['name'],
                    'amount': payload['paid'],
                    'payload': payload,
                    'extra_values': {'move_line_ids': [fields.Command.set((paid_lines | withheld_lines).ids)]},
                }
            )
        return details

    def _fill(self, declaration, facts):
        details = self._details(declaration, facts)
        values = {
            box: sum(d['amount'] for d in details if d['box_code'] == box) for _section, box, _label in self._sections
        }
        values[PAID] = sum(d['amount'] for d in details)
        if self._kind:
            values[WITHHELD] = sum(d['payload']['withheld'] for d in details)
        return values

    # --- contrôles ------------------------------------------------------------------------------

    def _checks(self, declaration, facts):
        issues = []
        for detail in self._details(declaration, facts):
            partner = self.env['res.partner'].browse(detail['partner_id'])
            payload = detail['payload']
            if not partner.l10n_ga_fee_category:
                message = self.env._('%(partner)s : bénéficiaire non classé (catégorie DGI).', partner=partner.name)
                issues.append((WARNING, 'GA_RAS_UNCLASSIFIED', message, partner))
            if self._nif_required and not payload['nif']:
                message = self.env._('%(partner)s : NIF absent.', partner=partner.name)
                issues.append((BLOCKING, 'GA_RAS_NO_NIF', message, partner))
            if self._kind and payload['paid'] and not payload['withheld']:
                message = self.env._(
                    '%(partner)s : %(paid)s versés sans retenue.', partner=partner.name, paid=payload['paid']
                )
                issues.append((WARNING, 'GA_RAS_MISSING', message, partner))
        return issues + self._monthly_issues(declaration, facts)

    def _monthly_issues(self, declaration, facts):
        """Retenues de l'annexe = Σ des déclarations mensuelles de l'année (ID26 ↔ ID18, ID24 ↔ ID27)."""
        if not self._monthly_type:
            return []
        declared = self.env['l10n_ga.declaration'].search(
            [
                ('company_id', '=', declaration.company_id.id),
                ('type_id.code', '=', self._monthly_type),
                ('date_from', '>=', declaration.date_from),
                ('date_to', '<=', declaration.date_to),
                ('state', '!=', 'cancel'),
            ],
            order='id',
        )
        latest = {}
        for decl in declared:
            latest[decl.date_from] = decl  # la dernière rectificative remplace l'originale
        expected = sum(line.value_amount for decl in latest.values() for line in decl.line_ids if line.code == WITHHELD)
        total = self._fill(declaration, facts).get(WITHHELD) or 0.0
        if not float_compare(total, expected, precision_digits=0):
            return []
        message = self.env._(
            'Retenues de l’année %(annex)s, déclarées sur les %(type)s : %(declared)s.',
            annex=total,
            type=self._monthly_type,
            declared=expected,
        )
        return [(BLOCKING, 'GA_DAS_MONTHLY', message, declaration)]

    # --- classeur ---------------------------------------------------------------------------------

    def _columns(self):
        env = self.env
        return [
            ('name', env._('Nom, prénom ou raison sociale')),
            ('nif', env._('NIF')),
            ('profession', env._('Profession, qualité ou fonction')),
            ('paid', env._('Sommes versées')),
        ]

    def _render_workbook(self, declaration):
        env = self.env
        company = declaration.company_id
        builder = XlsxDeclarationBuilder()
        columns = self._columns()
        blocks = [
            {
                'title': env._('Déclarant'),
                'pairs': [
                    (env._('Raison sociale'), company.name),
                    (env._('NIF'), company.l10n_ga_nif or company.vat or ''),
                    (env._('Exercice'), f'{declaration.date_to:%Y}'),
                ],
            }
        ]
        for section, _box, label in self._sections:
            details = declaration.detail_ids.filtered(lambda d, s=section: (d.payload or {}).get('section') == s)
            rows = [[(d.payload or {}).get(key) for key, _label in columns] for d in details]
            amount_keys = {'paid', 'withheld'}
            totals = [env._('Total')] + [
                sum(r[i] or 0 for r in rows) if columns[i][0] in amount_keys else None for i in range(1, len(columns))
            ]
            blocks.append(
                {'title': label, 'headers': [label for _key, label in columns], 'rows': rows, 'totals': totals}
            )
        builder.form(
            declaration.type_id.code,
            blocks,
            title=f'{declaration.type_id.code} — {declaration.type_id.name}',
            subtitle=declaration.name,
            landscape=True,
        )
        return builder.build()


class L10nGaDeclarationGeneratorId23(models.AbstractModel):
    """ID23 : commissions et honoraires versés au Gabon (art. 189), salariés (A) et non-salariés (B)."""

    _name = 'l10n_ga.declaration.generator.id23'
    _inherit = 'l10n_ga.declaration.generator.fees'
    _description = 'ID23 — commissions et honoraires versés au Gabon'

    @property
    def _sections(self):
        return (
            ('employee', 'PAID_EMPLOYEE', self.env._('A) Bénéficiaires ayant la qualité de salarié')),
            ('other', 'PAID_OTHER', self.env._('B) Bénéficiaires n’ayant pas la qualité de salarié')),
        )

    def _partner_domain(self, declaration):
        return [('l10n_ga_is_resident', '=', True), ('l10n_ga_fee_category', 'in', DAS_FEE_CATEGORIES)]

    def _section(self, declaration, partner):
        return 'employee' if partner._l10n_ga_is_employee(declaration.company_id) else 'other'


class L10nGaDeclarationGeneratorId24(models.AbstractModel):
    """ID24 : commissions et honoraires versés hors du Gabon (art. 189), CEMAC / hors CEMAC, retenue 20 %."""

    _name = 'l10n_ga.declaration.generator.id24'
    _inherit = 'l10n_ga.declaration.generator.fees'
    _description = 'ID24 — sommes versées hors du Gabon'

    _kind = 'ras_20'
    _monthly_type = 'ID27'
    _nif_required = False

    @property
    def _sections(self):
        return (
            ('cemac', 'PAID_CEMAC', self.env._('A) Bénéficiaires de la CEMAC')),
            ('other', 'PAID_OTHER', self.env._('B) Bénéficiaires hors CEMAC')),
        )

    def _partner_domain(self, declaration):
        return [('l10n_ga_is_resident', '=', False), ('l10n_ga_fee_category', '!=', False)]

    def _section(self, declaration, partner):
        return 'cemac' if partner.l10n_ga_zone == 'cemac' else 'other'

    def _columns(self):
        env = self.env
        return [
            ('name', env._('Nom, prénom ou raison sociale')),
            ('address', env._('Adresse du bénéficiaire')),
            ('paid', env._('Montant versé')),
            ('withheld', env._('Retenue à la source effectuée')),
        ]


class L10nGaDeclarationGeneratorId26(models.AbstractModel):
    """ID26 : sommes versées aux prestataires non assujettis à la TVA et retenues de 9,5 % (art. 182, 189)."""

    _name = 'l10n_ga.declaration.generator.id26'
    _inherit = 'l10n_ga.declaration.generator.fees'
    _description = 'ID26 — prestataires non assujettis à la TVA'

    _kind = 'ras_095'
    _monthly_type = 'ID18'

    @property
    def _sections(self):
        return (('provider', 'PAID_PROVIDER', self.env._('Prestataires de services non assujettis à la TVA')),)

    def _partner_domain(self, declaration):
        return [('l10n_ga_withholding_kind', '=', 'ras_095')]

    def _columns(self):
        env = self.env
        return [
            ('name', env._('Nom, prénom ou raison sociale du prestataire')),
            ('nif', env._('NIF du prestataire')),
            ('paid', env._('Montant versé')),
            ('withheld', env._('Montant de la retenue effectuée')),
        ]
