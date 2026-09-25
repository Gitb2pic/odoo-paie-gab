# Complétude — étape 3 : `l10n_ga_hr_payroll_account` (25/09/2026)

Plan `docs/plans/3.md` (« go avec tes recommandations », décisions D-58 à D-64).

## Score

**18 / 18 éléments attendus présents et testés (100 %)** ; 28 tests Odoo verts sur base neuve et en mise à jour ; installation sur société existante et désinstallation propres.

## C1 — Inventaire attendu / réel

| # | Élément attendu (source) | État | Fichier | Test |
|---|---|---|---|---|
| 1 | Manifeste `auto_install`, dépendances (prompt, `05` §3, D-63) | présent | `__manifest__.py` | installation auto constatée (base jetable) |
| 2 | Sécurité : aucun nouveau modèle → pas d'ACL ni de record rule | sans objet | — | — |
| 3 | Table règle → comptes (catalogue + `05` §2.4), 72 règles imputées | présent | `models/account_chart_template.py` (`RULE_ACCOUNTS`) | `test_table_covers_every_rule`, `test_table_matches_catalogue`, `test_every_template_account_exists` |
| 4 | Règles « sans écriture » justifiées (`GROSS`, `GA_ROUND_PREV`, `GA_ROUND`, `GA_NET_PAY`) | présent | `NO_ENTRY_RULES` | `test_cash_rounding_has_no_entry`, `test_table_covers_every_rule` |
| 5 | Liaison par `ref('pcg_*')` par société, pas de xml_id de compte en dur | présent | `_l10n_ga_configure_payroll_accounts` | `test_company_configured_at_chart_load` |
| 6 | Configuration au chargement du plan (nouvelle société) | présent | `_configure_payroll_account_ga` | `test_new_company_configured_when_chart_loaded` |
| 7 | Configuration des sociétés existantes à l'installation | présent | `data/account_chart_template_data.xml` | `test_install_hook_configures_existing_companies` + base jetable |
| 8 | Action de reconfiguration (écrase, D-60) | présent | `data/ir_actions_server_data.xml` | `test_server_action_overwrites` |
| 9 | Non-écrasement des réglages du comptable (D-60) | présent | idem | `test_existing_accounts_kept_unless_overwrite` |
| 10 | Journal de paie par société | présent | journal standard `hr_payroll_account_journal` lié à la structure Gabon | `test_one_balanced_move_per_payslip_without_adjustment` |
| 11 | 422 lettrable, paiement enregistrable (D-59) | présent | idem | `test_register_payment_on_422` |
| 12 | Tiers salarié sur 422, 4211, 4212 | présent | `data/hr_salary_rule_data.xml` | `test_net_credited_to_422_per_employee`, `test_loan_installment_credits_4211`, `test_advance_credits_4212` |
| 13 | Lot 3 salariés (virement, chèque, espèces) équilibré, rubriques sur leurs comptes, 422 = Σ NET | présent | — | `test_payroll_move.py` (10 tests) |
| 14 | Deux sociétés : comptes propres | présent (+ correction multi-société) | `models/hr_payslip.py` `_action_create_account_move` | `TestTwoCompanies` |
| 15 | Prêt retenu → crédit 4211 | présent | table | `test_loan_installment_credits_4211` |
| 16 | Avantages en nature 6617 / 781 (D-58) | présent | table | `test_benefit_in_kind_transfers_charges` |
| 17 | Contrôle bloquant `GA_NO_ACCOUNT` (lot et bulletin seul) | présent | `models/l10n_ga_payroll_check.py`, `models/hr_payslip.py` ; point d'extension `hr.payslip._l10n_ga_payroll_checks()` dans la paie | `test_missing_account_blocks_the_run`, `test_missing_account_blocks_single_payslip`, `test_check_skipped_without_payroll_journal`, `test_checks.py` (paie) |
| 18 | Rapprochements 447x / 431x réutilisables | présent | `res.company.l10n_ga_payroll_liability_balance` | `test_reconciliation.py` (4 tests) |

## C2 — Traçabilité

| Exigence | Code | Test |
|---|---|---|
| RG09 : au plus une pièce par bulletin ; regroupement par lot en option | standard `batch_payroll_move_lines` (inchangé) | `test_one_balanced_move_per_payslip_without_adjustment` |
| RG17 : au plus un compte débit et un compte crédit par règle | `RULE_ACCOUNTS` (clés `debit` / `credit`) | `test_table_*`, `test_each_rule_on_its_account` |
| Règle d'or 1 (aucun taux en dur) | aucun montant ni taux dans le module | C3 |
| Règle d'or 3 (une seule règle NET) | NET non redéfini, seulement `employee_move_line` | `test_table_covers_every_rule` |
| Règle d'or 11 (multi-société) | comptes `company_dependent`, pièces par société | `TestTwoCompanies`, `test_new_company_*` |
| Règle d'or 14 (dépendances) | dépend de la paie, jamais l'inverse ; la paie expose `_l10n_ga_payroll_checks()` | revue du manifeste |
| ADR-19 d / sprint 0 point 4 | `_configure_payroll_account_ga`, pas de XML de comptes | `test_company_configured_at_chart_load` |
| D-58 à D-64 | voir C1 | voir C1 |

## C3 — Chasse aux trous

| Contrôle | Résultat |
|---|---|
| TODO / stubs / `pass` / `...` | 0 |
| Manifeste ↔ fichiers | 3 fichiers de données, tous déclarés et présents |
| Droits / record rules | aucun nouveau modèle |
| Nombres littéraux | 0 (codes de comptes par xml_id de gabarit) |
| Syntaxe pré-19 | 0 |
| Méthodes sans test nommé | 5 surcharges ou fonctions internes exercées indirectement : `_configure_payroll_account_ga` (chargement du plan), `_action_create_account_move` (deux sociétés), `_l10n_ga_blocking_issues` et `missing_*` (tests `GA_NO_ACCOUNT`) |
| Messages traduisibles | `env._` ; `i18n/fr.po` et `.pot` générés |
| Warnings de configuration | un seul message par société (journal absent, comptes absents), vérifié par `assertLogs` |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur (ajout de `ignored-modules=odoo.addons.l10n_ga_hr_payroll` à `.pylintrc` : astroid ne peut pas greffer le dépôt sur le paquet `odoo` de Community ; imports vérifiés par les tests Odoo) |
| `make test-core` | 483 tests, couverture 100 % (noyau inchangé) |
| `make test MODULE=l10n_ga_hr_payroll_account` | 28 tests, 0 échec, 0 ERROR ; 5 WARNING d'environnement (`odoo.conf`, `pdfminer.six`) |
| `make upgrade MODULE=l10n_ga_hr_payroll_account` | 27 tests post-installation verts, 0 ERROR ; 10 WARNING d'environnement |
| `make test MODULE=l10n_ga_hr_payroll` (point d'extension ajouté, version 19.0.1.6.1) | 178 tests, 0 échec |
| Base jetable : `l10n_ga` + `hr_payroll_account`, société au plan « ga », puis installation de la paie | module comptable installé automatiquement ; journal SLR ; NET → 422000 lettrable ; 4 règles sans compte = les 4 « sans écriture » |
| Désinstallation | `uninstalled`, action serveur supprimée |

## C5 — Recette chiffrée

`test_recette_f16.py` : F16 (590 000 → net 514 897) payé en espèces (514 500 versés), pièce vérifiée compte par compte, **écart 0** :

| Compte | Solde |
|---|---|
| 6611 / 6634 / 6638 | 450 000 / 35 000 / 105 000 (débit) |
| 6641 | 122 655 (CNSS patronale 99 900 + CNAMGS 22 755) |
| 6413 / 6415 | 16 650 / 2 775 |
| 4311 + 4312 + 4313 | −127 650 (patronale 99 900 + salariale 27 750) |
| 4318 | −33 855 · 4471 −23 195 · 4472 −32 483 |
| 422 | −514 897 (le reliquat d'arrondi 397 reste dans 422) |

## Bloquants et questions pour Alex

Aucun bloquant. D-47 (mentions du bulletin, étape 2.7) reste à confirmer, sans lien avec cette étape.

## Dette technique acceptée

- Personnel non national en 6641 (D-61) ; plan `ga_syscebnl` non pris en charge, signalé par `GA_NO_ACCOUNT` (D-62) ; décaissement des prêts saisi à la main (D-64).
- À la désinstallation, `employee_move_line` reste coché sur `NET`, `GA_LOAN`, `GA_ADVANCE` (champ de `hr_payroll_account`, sans effet sans ce module), comme les comptes posés par société : comportement standard des données de configuration.
- Les soldes de rapprochement ne lisent que les écritures comptabilisées (brouillons exclus, testé).
