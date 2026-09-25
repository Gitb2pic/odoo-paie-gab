from odoo import api, fields, models

from ..lib.ga_fiscal_core.param_codes import PARAMETERS, params_from_values

CASH_ROUNDING_DEFAULT_CODE = 'l10n_ga_cash_rounding_default'


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ga_nif = fields.Char(string='NIF (Gabon)')
    l10n_ga_cnss_number = fields.Char(string='N° employeur CNSS')
    l10n_ga_cnamgs_number = fields.Char(string='N° employeur CNAMGS')
    l10n_ga_tax_center = fields.Char(
        string='Centre des impôts', help='Code résidence du centre des impôts d’affectation (cellule K33 de l’ID10).'
    )
    l10n_ga_segment = fields.Selection(
        [('dge', 'DGE'), ('cime', 'CIME'), ('other', 'Autre')],
        string='Segment fiscal',
        default='other',
        help='DGE et CIME : paiement des impôts par virement obligatoire.',
    )
    l10n_ga_cfp_declaration = fields.Selection(
        [('id10', 'Sur l’ID10'), ('id28', 'Sur l’ID28')],
        string='Déclaration de la CFP',
        default='id10',
        help='La CFP est déclarée une seule fois, sur l’un des deux imprimés (usage du centre des impôts à confirmer).',
    )
    l10n_ga_cfp_base = fields.Selection(
        [('social', 'Assiette sociale'), ('gross', 'Salaire brut')],
        string='Assiette de la CFP',
        default='social',
        help='Décision D-10 : assiette sociale par défaut (cas de référence), brut disponible en option.',
    )
    l10n_ga_entry_exit_hours = fields.Selection(
        [
            ('deduct', 'Retirer les heures hors contrat (comme une absence)'),
            ('prorata', 'Prorata des heures du contrat sur les heures prévues du mois'),
        ],
        string='Entrée / sortie en cours de mois',
        default='deduct',
        required=True,
        help='Salaire de base sur le mois de référence (FIX 01, D-104) : (a) référence − heures hors contrat ; '
        '(b) référence × heures du contrat / heures prévues du mois.',
    )
    l10n_ga_cash_rounding = fields.Integer(
        string='Arrondi des paies en espèces',
        default=lambda self: self._l10n_ga_default_cash_rounding(),
        help='Montant versé en espèces arrondi au multiple inférieur ; le reliquat est reporté. 0 = pas d’arrondi.',
    )
    l10n_ga_cnss_subrogation = fields.Boolean(
        string='Subrogation CNSS (maternité, accident du travail)',
        default=True,
        help='Vrai : salaire maintenu pendant la maternité et l’accident du travail, indemnités journalières '
        'remboursées par la CNSS à l’employeur. Faux : ces jours sortent du salaire de base (décision D-26).',
    )
    l10n_ga_loan_outstanding_cap = fields.Monetary(
        string='Plafond d’encours des prêts', help='Encours total des prêts d’un salarié. 0 = pas de plafond.'
    )

    @api.model
    def _l10n_ga_default_cash_rounding(self):
        value = self.env['hr.rule.parameter']._get_parameter_from_code(
            CASH_ROUNDING_DEFAULT_CODE, fields.Date.today(), raise_if_not_found=False
        )
        return int(value or 0)

    def _l10n_ga_fiscal_params(self, on_date, raise_if_not_found=False):
        """``FiscalParams`` en vigueur à ``on_date`` (RG06) avec les options de la société.

        Paramètres absents (module en cours d'installation) : ``None``, ou ``UserError``
        standard si ``raise_if_not_found``.
        """
        self.ensure_one()
        Parameter = self.env['hr.rule.parameter'].sudo()
        values = {}
        for spec in PARAMETERS:
            if spec.field is None:
                continue
            value = Parameter._get_parameter_from_code(spec.code, on_date, raise_if_not_found=raise_if_not_found)
            if value is None:
                return None
            values[spec.code] = value
        return params_from_values(values, cash_rounding=self.l10n_ga_cash_rounding, cfp_base=self.l10n_ga_cfp_base)
