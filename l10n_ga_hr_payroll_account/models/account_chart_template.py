"""Imputation SYSCOHADA des règles de la paie gabonaise (étape 3, `05` §2.4, RG17).

Les comptes des règles sont ``company_dependent`` (sprint 0 point 4, ADR-19 d) : ils sont posés par
société au chargement du plan « ga » (``_configure_payroll_account_ga``, appelé par
``E/hr_payroll_account/models/account_chart_template.py:16-24``), à l'installation pour les sociétés
existantes et par l'action « Configurer les comptes de paie Gabon ». Les comptes sont retrouvés par
leur xml_id de gabarit ``pcg_*`` (``ref`` par société, ``C/addons/account/models/chart_template.py:1232``).
"""

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

STRUCTURE = 'l10n_ga_hr_payroll.structure_ga_employee'
JOURNAL = 'hr_payroll_account_journal'
NET_ACCOUNT = 'pcg_422'

# Code de règle → xml_id de gabarit du compte, par clé standard « debit » / « credit ».
# Source : colonne ``account`` du catalogue (vérifiée par test) ; contreparties de `05` §2.4.
RULE_ACCOUNTS = {
    # Gains (montant positif → débit ; rappel négatif → crédit)
    'BASIC': {'debit': 'pcg_6611'},
    'GA_SURSAL': {'debit': 'pcg_6611'},
    'GA_ANC': {'debit': 'pcg_6612'},
    'GA_HS_J': {'debit': 'pcg_6611'},
    'GA_HS_N': {'debit': 'pcg_6611'},
    'GA_HS_DIM': {'debit': 'pcg_6611'},
    'GA_HS_FER': {'debit': 'pcg_6611'},
    'GA_RECALL': {'debit': 'pcg_6611'},
    'GA_FONCT': {'debit': 'pcg_6618'},
    'GA_INTERIM': {'debit': 'pcg_6612'},
    'GA_ASSID': {'debit': 'pcg_6612'},
    'GA_NUIT': {'debit': 'pcg_6612'},
    'GA_QUART': {'debit': 'pcg_6612'},
    'GA_RISQUE': {'debit': 'pcg_6612'},
    'GA_PENIB': {'debit': 'pcg_6612'},
    'GA_TECHN': {'debit': 'pcg_6612'},
    'GA_SUJET': {'debit': 'pcg_6612'},
    'GA_DIPLOME': {'debit': 'pcg_6612'},
    'GA_VIECHERE': {'debit': 'pcg_6638'},
    'GA_EXPAT': {'debit': 'pcg_6633'},
    'GA_ELOIGN': {'debit': 'pcg_6638'},
    'GA_LOGT_ESP': {'debit': 'pcg_6631'},
    'GA_RESP': {'debit': 'pcg_6638'},
    'GA_REPR': {'debit': 'pcg_6632'},
    'GA_CAISSE': {'debit': 'pcg_6638'},
    'GA_REND': {'debit': 'pcg_6612'},
    'GA_13M': {'debit': 'pcg_6612'},
    'GA_PFA': {'debit': 'pcg_6612'},
    'GA_BONUS': {'debit': 'pcg_6612'},
    'GA_BILAN': {'debit': 'pcg_6612'},
    'GA_RESULT': {'debit': 'pcg_6612'},
    'GA_GRATIF': {'debit': 'pcg_6612'},
    'GA_TRANSP': {'debit': 'pcg_6634'},
    'GA_VEHIC': {'debit': 'pcg_6634'},
    'GA_CARBU': {'debit': 'pcg_6634'},
    'GA_KILOM': {'debit': 'pcg_6634'},
    'GA_DEPL': {'debit': 'pcg_6638'},
    'GA_PANIER': {'debit': 'pcg_6638'},
    'GA_SALISS': {'debit': 'pcg_6638'},
    'GA_VESTIM': {'debit': 'pcg_6638'},
    'GA_BLANCH': {'debit': 'pcg_6638'},
    'GA_COIFF': {'debit': 'pcg_6638'},
    'GA_TROUSS': {'debit': 'pcg_6616'},
    'GA_SCOLAR': {'debit': 'pcg_6616'},
    'GA_JARDIN': {'debit': 'pcg_6616'},
    'GA_TRANSP_ENF': {'debit': 'pcg_6616'},
    'GA_SOLID': {'debit': 'pcg_6638'},
    'GA_COMPL_IJ': {'debit': 'pcg_6615'},
    'GA_CONGE': {'debit': 'pcg_6613'},
    'GA_ICCP': {'debit': 'pcg_6613'},
    'GA_PREAV': {'debit': 'pcg_6614'},
    'GA_LICENC': {'debit': 'pcg_6614'},
    'GA_ISR_RET': {'debit': 'pcg_6614'},
    'GA_ISR_DEM': {'debit': 'pcg_6614'},
    'GA_ISR_PS': {'debit': 'pcg_6614'},
    # Avantages en nature, hors NET : charge 6617, transfert de charges 781 (D-58)
    'GA_AN_LOGT': {'debit': 'pcg_6617', 'credit': 'pcg_781'},
    'GA_AN_DOM': {'debit': 'pcg_6617', 'credit': 'pcg_781'},
    'GA_AN_EAU': {'debit': 'pcg_6617', 'credit': 'pcg_781'},
    'GA_AN_NOUR': {'debit': 'pcg_6617', 'credit': 'pcg_781'},
    # Retenues : montant négatif sur la clé « debit » → crédit
    # (convention E/l10n_be_hr_payroll_account/models/account_chart_template.py:90)
    'GA_CNSS_SAL': {'debit': 'pcg_4313'},
    'GA_CNAMGS_SAL': {'debit': 'pcg_4318'},
    'GA_TCS': {'debit': 'pcg_4472'},
    'GA_IRPP': {'debit': 'pcg_4471'},
    'GA_IRPP_REGUL': {'debit': 'pcg_4471'},
    'GA_FNH_SAL': {'debit': 'pcg_4472'},
    'GA_ADVANCE': {'debit': 'pcg_4212'},
    'GA_LOAN': {'debit': 'pcg_4211'},
    'GA_ASSIGN': {'debit': 'pcg_4231'},
    'GA_GARNISH': {'debit': 'pcg_4232'},
    # Net dû au salarié
    'NET': {'credit': 'pcg_422'},
    # Charges patronales : 6641 pour tout le personnel en V1 (D-61)
    'GA_CNSS_PF': {'debit': 'pcg_6641', 'credit': 'pcg_4311'},
    'GA_CNSS_AT': {'debit': 'pcg_6641', 'credit': 'pcg_4312'},
    'GA_CNSS_AVID': {'debit': 'pcg_6641', 'credit': 'pcg_4313'},
    'GA_CNAMGS_PAT': {'debit': 'pcg_6641', 'credit': 'pcg_4318'},
    'GA_FNH': {'debit': 'pcg_6413', 'credit': 'pcg_4472'},
    'GA_CFP': {'debit': 'pcg_6415', 'credit': 'pcg_4472'},
}

# Règles sans écriture propre : totaux et arrondi espèces (le reliquat reste dans 422, F2).
NO_ENTRY_RULES = ('GROSS', 'GA_ROUND_PREV', 'GA_ROUND', 'GA_NET_PAY')


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _configure_payroll_account_ga(self, companies):
        self._l10n_ga_configure_payroll_accounts(companies)

    @api.model
    def _l10n_ga_configure_payroll_accounts(self, companies, overwrite=False):
        """Journal de la structure Gabon, comptes des règles et 422 lettrable, par société.

        Sans ``overwrite``, seuls les comptes vides sont remplis (décision D-60).
        """
        structure = self.env.ref(STRUCTURE, raise_if_not_found=False)
        if not structure:
            return
        for company in companies:
            chart = self.with_company(company)
            journal = chart.ref(JOURNAL, raise_if_not_found=False)
            company_structure = structure.with_company(company)
            if not journal:
                _logger.warning('Paie Gabon : journal des salaires absent pour la société %s.', company.name)
            elif overwrite or not company_structure.journal_id:
                company_structure.journal_id = journal
            missing = set()
            for rule in structure.rule_ids.with_company(company):
                for key, template_xmlid in RULE_ACCOUNTS.get(rule.code, {}).items():
                    field_name = f'account_{key}'
                    if rule[field_name] and not overwrite:
                        continue
                    account = chart.ref(template_xmlid, raise_if_not_found=False)
                    if account:
                        rule[field_name] = account
                    else:
                        missing.add(template_xmlid)
            if missing:
                _logger.warning(
                    'Paie Gabon : comptes %s absents pour la société %s (règles laissées sans compte).',
                    ', '.join(sorted(missing)),
                    company.name,
                )
            # D-59 : le compte du net doit être lettrable pour « Enregistrer un paiement »
            # (E/hr_payroll_account/models/hr_payslip.py:303-304).
            net_account = chart.ref(NET_ACCOUNT, raise_if_not_found=False)
            if net_account and not net_account.reconcile:
                net_account.reconcile = True
