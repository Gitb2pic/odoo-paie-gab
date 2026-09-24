# Complétude — `l10n_ga_hr_payroll`, étape 2.6 (import Excel F3, contrôles avant paie F8, arrondi espèces F2, cumuls d'ouverture F12)

Date : 24/09/2026 — plan : `docs/plans/2.6.md` (« go avec tes recommandations » ; P1 à P9 → D-38 à D-46).

## Score

**22 / 22 éléments attendus présents et testés = 100 %.** Aucun bloquant.

## C1 — Inventaire attendu / réel

| # | Élément attendu (prompt 2.6, F2, F3, F8, F12, RG23, RG25, RG26, ADR-18) | État | Emplacement |
|---|---|---|---|
| 1 | assistant `l10n_ga.payslip.input.import` | présent | `wizard/l10n_ga_payslip_input_import.py` + vue |
| 2 | modèle Excel du lot : une ligne par salarié, une colonne par type d'entrée actif et par type d'HS | présent | `_template_bytes` (`xlsxwriter`) ; `GA_LOAN` exclu ; 4 colonnes d'heures `GA_HS_*` |
| 3 | lecture `openpyxl` | présent | `_read_workbook` (`read_only`, `data_only`) ; fichier absent / illisible → `UserError` |
| 4 | étapes indépendantes testables (lecture, en-têtes, salarié, type, montant, lot, doublons) | présent | noyau pur `lib/ga_fiscal_core/input_import.py` : `normalise_headers`, `resolve_columns`, `resolve_employee`, `check_in_batch`, `dedupe`, `parse_amounts` (patron 13) |
| 5 | aperçu des anomalies | présent | `action_preview` : lignes acceptées / refusées, messages traduits par ligne et colonne |
| 6 | écriture dans `hr.payslip.input` et `hr.work.entry` (heures décimales) | présent | `_write_amount` (D-42), `_write_hours` + `spread_hours` (D-43) ; marqueurs `l10n_ga_imported` |
| 7 | recalcul du lot | présent | `_compute_worked_days_line_ids` puis `compute_sheet` des bulletins modifiés |
| 8 | `l10n_ga.check.issue` selon ADR-18 | présent | `models/l10n_ga_check_issue.py` (périmètre `payslip_run`, extensible par `l10n_ga_dgi_edi`) |
| 9 | chaîne `PAYROLL_CHECKS` (CNSS, NIF, situation, embauche, parts forcées, grille, banque, version, prêt > 40 %, indemnité forcée) | présent | `models/l10n_ga_payroll_check.py` : 10 contrôles, gravités D-39 |
| 10 | lot bloqué s'il reste une anomalie bloquante (RG26) | présent | `compute_sheet` ne calcule aucun bulletin d'un lot bloqué ; `action_confirm` refusé (D-38) |
| 11 | pont natif (ADR-18 §4) | présent | `_get_errors_by_slip` / `_get_warnings_by_slip`, dépendance `l10n_ga_issue_ids.severity` |
| 12 | `hr_payslip_run.py` : date de paiement du lot, bouton « Contrôler » | présent | `l10n_ga_payment_date` (D-46) reprise par les bulletins ; boutons « Contrôler », « Importer les variables », « Anomalies » |
| 13 | règles `GA_ROUND_PREV`, `GA_ROUND`, `GA_NET_PAY` après `NET` unique | présent | catalogue (séquences 201-203, catégorie `GA_CASH`), `CASH_VALUES` du noyau, `_l10n_ga_cash_value` |
| 14 | champ `l10n_ga_rounding_carry` | présent | figé à la validation (`−GA_ROUND`) |
| 15 | reliquat versé au solde de tout compte | présent | `cash_round(final=…départ)` |
| 16 | `l10n_ga.ytd.opening` unique salarié × année (RG25) | présent | `models.Constraint('UNIQUE(employee_id, year)')` ; période dans l'année ; verrou après usage |
| 17 | intégration aux cumuls (régularisation IRPP, compteur 4 000 000, DAS) | présent | `_l10n_ga_ytd` ajoute l'ouverture → faits du noyau et cumuls figés `l10n_ga_ytd_*` (lus par la DAS) |
| 18 | vues, menus, droits, règles multi-société | présent | 3 fichiers de vues, 2 menus, bouton « Cumuls d'ouverture » ; 5 lignes d'accès ; 2 règles `company_id in company_ids` |
| 19 | `test_input_import.py` (lignes fausses, doublons, aperçu, décimales) | présent | Odoo : 11 tests ; pur : 17 tests |
| 20 | tests des contrôles (chaque règle) | présent | `tests/test_checks.py` : 21 tests |
| 21 | `test_rounding.py` côté Odoo sur 12 bulletins | présent | `tests/test_rounding.py` : 8 tests + recette F16 espèces |
| 22 | bascule en cours d'année avec cumuls d'ouverture | présent | `tests/test_ytd_opening.py` : 7 tests |

## C2 — Traçabilité exigence → code → test

| Exigence | Code | Test |
|---|---|---|
| F3 (modèle, validation, aperçu, écriture, décimales) | assistant + `input_import.py` | `test_template`, `test_template_round_trip_imports_nothing`, `test_preview_*`, `test_import_amounts_and_decimal_hours_then_recompute`, `test_reimport_replaces_and_zero_deletes`, `test_empty_cell_leaves_value_unchanged`, `test_hours_spread_over_days_below_24h`, `test_hours_over_capacity_rejected_at_write`, `test_unreadable_or_missing_file`, `test_missing_key_column` ; noyau `test_input_import.py` |
| F8 / patron 8 | `PAYROLL_CHECKS`, `run_checks` | `test_chain_is_the_documented_sequence`, un test par contrôle, `test_checks_are_idempotent`, `test_abstract_rule_and_custom_chain` |
| RG26 | `compute_sheet`, `action_confirm` | `test_blocking_issue_prevents_run_computation`, `test_generate_payslips_creates_but_does_not_compute_blocked_run`, `test_warnings_do_not_block` |
| ADR-18 (modèle unique, pont natif, multi-société) | `l10n_ga.check.issue`, `_get_errors_by_slip` | `test_native_bridge_blocks_validation`, `test_issue_company_and_record_rule` |
| F2 / RG23 / patron 15 | `GA_ROUND*`, `_l10n_ga_cash`, `l10n_ga_rounding_carry` | `test_twelve_consecutive_cash_payslips`, `test_transfer_pays_net`, `test_switch_to_transfer_pays_previous_carry`, `test_final_settlement_pays_whole_carry`, `test_no_rounding_step`, `test_carry_frozen_after_validation`, `test_cancelled_payslip_carry_ignored`, `test_f16_paid_in_cash_rounded_to_500` |
| Règle d'or 3 (NET unique) | catalogue ; générateur | `test_cash_rounding_rules_after_single_net`, `test_net_is_not_modified_by_rounding`, `test_rule_codes_unique` |
| F12 / RG25 | `l10n_ga.ytd.opening`, `_l10n_ga_ytd` | `test_switch_in_july_gives_same_year_end_as_full_year`, `test_bonus_cap_counter_includes_opening`, `test_opening_ignored_for_payslip_in_covered_period`, `test_one_opening_per_employee_and_year`, `test_period_within_year`, `test_locked_once_used_by_validated_payslip`, `test_employee_button` |
| F7 (figé) | reliquat et cumuls d'ouverture figés à la validation | `test_carry_frozen_after_validation`, `test_locked_once_used_by_validated_payslip` |
| D-46 (date de paiement du lot) | `l10n_ga_payment_date` | `test_payment_date_of_run_goes_to_slips`, `test_complete_employee_has_no_issue_and_is_computed` |
| Règle d'or 1 (aucun taux en dur) | ratio prêt = paramètre daté ; pas d'arrondi = option société | `test_no_numeric_literal_in_formulas` (outillage), `test_loan_installment_over_ratio` |
| Règle d'or 10 (xlsxwriter pour les neufs, openpyxl en lecture) | assistant | `test_template` (relit le modèle avec openpyxl) |
| Règle d'or 11 (multi-société) | `company_id` requis, `check_company`, règles | `test_issue_company_and_record_rule` |

## C3 — Chasse aux trous

| Contrôle | Résultat |
|---|---|
| `TODO`, `FIXME`, `pass`, `...`, `NotImplementedError` | 1 : `CheckRule.run` (interface abstraite documentée du patron 8, testée) |
| fichiers du manifeste absents / non déclarés | 0 / 0 |
| modèles sans accès / sans règle multi-société | 0 / 0 (assistant transitoire : rattaché au lot, sans règle) |
| champs de vue inexistants | 0 (installation et mise à jour) |
| nombres littéraux | aucun taux ; largeurs de colonnes et 24 h/jour (contrainte standard) en constantes nommées |
| `import odoo` dans le noyau | 0 (test AST) |
| syntaxe pré-19 | 0 |
| libellés non traduisibles | 0 (`self.env._`) ; `.pot` / `fr.po` régénérés |
| méthodes publiques sans test | 0 |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | outillage 65 passés ; noyau **466** passés, couverture **100 %** |
| `make test MODULE=l10n_ga_hr_payroll` | base neuve : code 0, **156 tests**, 0 ERROR/CRITICAL |
| `make upgrade MODULE=l10n_ga_hr_payroll` | code 0, 155 tests (avant le dernier test ajouté), 0 ERROR/CRITICAL ; avertissements : configuration du serveur, `pdfminer` |
| installation puis désinstallation (base `test_ga_` supprimée ensuite) | `uninstalled`, 0 table, 0 colonne `l10n_ga_*`, 0 paramètre, 0 règle `GA_*` |
| `make i18n` | code 0 |

Corrigé pendant C4 : `marital` est NOT NULL en base → le contrôle `GA_NO_MARITAL` vise « absente ou inconnue du quotient familial » ; attribut de test `run` qui masquait `TestCase.run` ; contrainte de période testée sous point de sauvegarde ; code d'entrée de test inexistant ; texte d'aperçu vide stocké `False` ; `string` redondants signalés par pylint-odoo (dont deux anciens de 2.5) ; bibliothèques Excel et `python-dateutil` ajoutées au venv de dev pour l'analyse statique (`docs/environnement_vps.md`).

## C5 — Recette chiffrée

| Cas | Attendu | Obtenu | Écart |
|---|---|---|---|
| F16 (590 000) payé en espèces, arrondi 500 | NET 514 897, `GA_ROUND` −397, versé 514 500, reliquat 397 | idem | 0 |
| F16 et profils 2.3 à 2.5 | inchangés (net 514 897) | verts | 0 |
| 12 mois en espèces (401 237, primes trimestrielles) | versé + reliquat final = somme des NET ; versé multiple de 500 ; reliquat ∈ [0 ; 500[ | idem | 0 |
| bascule en juillet avec cumuls d'ouverture = témoin payé toute l'année | IRPP, régularisation de décembre, NET et 7 cumuls figés identiques au témoin, mois par mois | idem (≤ 1 FCFA) | 0 |
| gratification 1 500 000 après 3 400 000 exonérés en ouverture | exonéré 600 000 (plafond 4 000 000) ; sans ouverture 1 500 000 | idem | 0 |
| import 7,5 h d'HS jour | prestation 7,5 h, `GA_HS_J` calculé | idem | — |
| import 30,5 h | réparties sur 2 jours, ≤ 24 h/jour, depuis le dernier jour | idem | — |

## Bloquants et questions pour Alex

Aucun.

## Dette technique acceptée

- Les anomalies sont recalculées à chaque `compute_sheet` d'un bulletin de lot (coût d'une chaîne par lot) : simple et toujours à jour ; à revoir seulement si un lot de plusieurs milliers de bulletins devient lent.
- Contrôle `GA_NO_VERSION` : un bulletin sans version valide n'est normalement pas créé par le standard ; le contrôle couvre les créations manuelles et les reprises.
- Les états de billetage et de virements (F2) sont livrés à l'étape 2.7, comme prévu.
