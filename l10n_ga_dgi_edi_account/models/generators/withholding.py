"""ID18 et ID27 : retenues à la source du mois, lues sur les paiements validés (sprint 0 point 7).

Voir ``payments.py`` : lignes de retenue des paiements, avoir en négatif, écriture jointe au détail
quand elle existe. Les cellules d'en-tête sont en données (cases) ; la liste nominative des bordereaux
est décrite ici (mise en page du gabarit officiel, pas une règle fiscale).
"""

from odoo import fields, models
from odoo.addons.l10n_ga_dgi_edi.models.declaration_generator import BLOCKING, WARNING
from odoo.tools import float_round

from .payments import supplier_payments, withholding_by_partner

BASE, WITHHELD = 'TOTAL_BASE', 'TOTAL_WITHHELD'


class L10nGaDeclarationGeneratorWithholding(models.AbstractModel):
    _name = 'l10n_ga.declaration.generator.withholding'
    _inherit = 'l10n_ga.declaration.generator.base'
    _description = 'Retenues à la source du mois (base commune ID18 / ID27)'

    _kind = None  # nature de retenue (account.tax.l10n_ga_withholding_kind)
    # (feuille, 1re ligne, capacité, colonnes (numéro, nom ou pays…, base, retenue), ligne de total ou None)
    _layout = ()
    _nif_required = True

    def _applies(self, company):
        return bool(self.env['account.tax']._l10n_ga_withholding_taxes(company, self._kind))

    def _requires_cnss_number(self, declaration):
        return False

    def _taxes(self, declaration, kind=None):
        return self.env['account.tax']._l10n_ga_withholding_taxes(declaration.company_id, kind or self._kind)

    def _by_partner(self, declaration, kind=None):
        taxes = self._taxes(declaration, kind)
        return withholding_by_partner(
            self.env, declaration.company_id, declaration.date_from, declaration.date_to, taxes
        )

    def _collect(self, declaration):
        return {'partners': dict(self._by_partner(declaration))}

    def _payload(self, partner, item):
        return {
            'nif': partner.vat or '',
            'name': partner.name or '',
            'country': partner.country_id.name or '',
            'base': float_round(item['base'], precision_digits=0),
            'withheld': float_round(item['withheld'], precision_digits=0),
            'payments': ', '.join(item['payments'].mapped('name')),  # l'écriture n'existe qu'une fois rapprochée
        }

    def _details(self, declaration, facts):
        details = []
        for partner, item in sorted(facts['partners'].items(), key=lambda i: (i[0].name or '', i[0].id)):
            payload = self._payload(partner, item)
            details.append(
                {
                    'box_code': WITHHELD,
                    'partner_id': partner.id,
                    'label': partner.name,
                    'amount': payload['withheld'],
                    'payload': payload,
                    'extra_values': {'move_line_ids': [fields.Command.set(item['lines'].ids)]},
                }
            )
        return details

    def _fill(self, declaration, facts):
        details = self._details(declaration, facts)
        return {
            BASE: sum(d['payload']['base'] for d in details),
            WITHHELD: sum(d['payload']['withheld'] for d in details),
        }

    def _row(self, detail):
        payload = detail.payload or {}
        return [payload.get('nif'), payload.get('name'), payload.get('base'), payload.get('withheld')]

    # --- contrôles ------------------------------------------------------------------------------

    def _checks(self, declaration, facts):
        issues = []
        for partner in facts['partners']:
            if not partner.l10n_ga_fee_category:
                message = self.env._('%(partner)s : bénéficiaire non classé (catégorie DGI).', partner=partner.name)
                issues.append((WARNING, 'GA_RAS_UNCLASSIFIED', message, partner))
            if self._nif_required and not partner.vat:
                message = self.env._('%(partner)s : NIF absent.', partner=partner.name)
                issues.append((BLOCKING, 'GA_RAS_NO_NIF', message, partner))
        return issues + self._double_issues(declaration, facts) + self._missing_issues(declaration, facts)

    def _double_issues(self, declaration, facts):
        """Double retenue (RG27) : un même bénéficiaire retenu à 9,5 % et à 20 % sur la période."""
        other_kind = ({'ras_095', 'ras_20'} - {self._kind}).pop()
        doubled = self.env['res.partner'].concat(*self._by_partner(declaration, other_kind)) & self.env[
            'res.partner'
        ].concat(*facts['partners'])
        wrong = self.env['res.partner'].concat(
            *(p for p in facts['partners'] if self._kind == 'ras_095' and not p.l10n_ga_is_resident)
        )
        return [
            (
                BLOCKING,
                'GA_RAS_DOUBLE',
                self.env._(
                    '%(partner)s : retenues de 9,5 %% et de 20 %% cumulées ou non-résident retenu à 9,5 %%.',
                    partner=p.name,
                ),
                p,
            )
            for p in doubled | wrong
        ]

    def _missing_issues(self, declaration, facts):
        """Fournisseur classé payé dans la période sans retenue (paiement groupé, retenue supprimée…)."""
        payments = supplier_payments(
            self.env,
            declaration.company_id,
            declaration.date_from,
            declaration.date_to,
            [('payment_type', '=', 'outbound'), ('partner_id.l10n_ga_withholding_kind', '=', self._kind)],
        )
        missing = payments.filtered(
            lambda p: not p.withholding_line_ids.tax_id.filtered(lambda t: t.l10n_ga_withholding_kind == self._kind)
        )
        return [
            (
                WARNING,
                'GA_RAS_MISSING',
                self.env._(
                    '%(payment)s : paiement de %(partner)s sans retenue.', payment=p.name, partner=p.partner_id.name
                ),
                p,
            )
            for p in missing
        ]

    # --- gabarit officiel -----------------------------------------------------------------------

    def _fill_template(self, declaration, renderer):
        """Liste nominative : zones du bordereau puis feuillets supplémentaires, copiés au besoin."""
        rows = [self._row(detail) for detail in declaration.detail_ids]
        layout = list(self._layout)
        capacity = sum(zone[2] for zone in layout)
        extra = 0
        while len(rows) > capacity:  # feuillets supplémentaires : copies de la dernière zone
            extra += 1
            sheet, start, size, columns, total = layout[-1]
            title = renderer.copy_sheet(self._layout[-1][0], f'{self._layout[-1][0].strip()} ({extra + 1})')
            layout.append((title, start, size, columns, total))
            capacity += size
        offset = 0
        for index, (sheet, start, size, columns, total) in enumerate(layout):
            chunk = rows[offset : offset + size]
            if index and not chunk:  # feuillet supplémentaire inutile : retiré du classeur
                renderer.remove_sheet(sheet)
                continue
            renderer.rows(sheet, start, chunk, columns, capacity=size)
            if total:
                renderer.boxes(
                    [
                        (f"'{sheet}'!{columns[-2]}{total}", sum(r[-2] or 0 for r in chunk), '#,##0'),
                        (f"'{sheet}'!{columns[-1]}{total}", sum(r[-1] or 0 for r in chunk), '#,##0'),
                    ]
                )
            offset += size
