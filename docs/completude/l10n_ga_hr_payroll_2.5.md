# Complétude — `l10n_ga_hr_payroll`, étape 2.5 (prêts salariés F1, indemnités récurrentes F15)

Date : 24/09/2026 — plan : `docs/plans/2.5.md` (« go avec tes recommandations » ; P1 à P9 → D-29 à D-37).

## Score

**20 / 20 éléments attendus présents et testés = 100 %.** Aucun bloquant.

## C1 — Inventaire attendu / réel

| # | Élément attendu (prompt 2.5, F1, F15, RG19-RG21, RG28, ADR-16) | État | Emplacement |
|---|---|---|---|
| 1 | `l10n_ga.employee.loan` (`mail.thread`, séquence, états brouillon / approuvé / en cours / soldé / annulé) | présent | `models/l10n_ga_employee_loan.py` ; séquence `PRET/%(year)s/` (2.2) |
| 2 | `l10n_ga.employee.loan.line` (à payer / retenue / reportée ; + remboursée hors paie, D-33) | présent | idem |
| 3 | octroi par spécifications combinables (ancienneté, 40 % du net, encours ≤ plafond) | présent | noyau `loans.py` (patron 12) ; seuils = paramètres datés (D-37), plafond = option société |
| 4 | dérogation RH motivée et tracée | présent | contrainte de motif ; utilisateur, date, conditions levées dans le chatter |
| 5 | remboursement anticipé | présent | assistant `l10n_ga.loan.early.repayment` (hors paie / sur bulletin) |
| 6 | report d'échéance | présent | `action_postpone` (D-34) |
| 7 | solde restant proposé au solde de tout compte (quotité saisissable) | présent | `_l10n_ga_due_loan_lines`, `_l10n_ga_cap_departure_loan` ; barème art. 729 CPC en paramètre daté (D-32) |
| 8 | entrée `GA_LOAN` alimentée par les échéances de la période | présent | `_l10n_ga_loan_inputs` dans `compute_sheet` (sprint 0 point 6) |
| 9 | échéance « retenue » à la validation (RG21) | présent | `_l10n_ga_withhold_loan_lines` ; retour « à payer » à l'annulation / au brouillon (D-30) |
| 10 | indemnités : extension de `hr.salary.attachment` (ADR-16, D-29) | présent | `models/hr_salary_attachment.py` |
| 11 | mode fixe / % du salaire de la version / quantité × taux | présent | noyau `allowances.py`, `_l10n_ga_amount` |
| 12 | forcée imposable + motif obligatoire, transmise au noyau | présent | contrainte ; `l10n_ga_forced_taxable` sur l'entrée ; `GainLine(forced_taxable=True)` scindée (D-36) |
| 13 | non-chevauchement (RG28, `@api.constrains`) | présent | `_check_l10n_ga_overlap` (indemnités ouvertes, même type, même salarié) |
| 14 | `_l10n_ga_allowance_inputs()` : entrées marquées `l10n_ga_allowance_id`, prorata des jours de validité | présent | `hr_payslip.py` (après `_compute_input_line_ids` et avant le calcul) ; D-35 |
| 15 | une entrée manuelle du même type remplace l'automatique | présent | `manual_priority` au calcul |
| 16 | vues : liste sur la fiche salarié, bouton « Indemnités », écrans des prêts | présent | page standard « Ajustements » + bloc Gabon ; boutons « Indemnités » et « Prêts » ; formulaire, liste, recherche, menu Paie → Salariés → Prêts salariés |
| 17 | droits et règles multi-société | présent | 5 lignes d'accès (prêt, échéance, assistant) ; 2 règles `company_id in company_ids` |
| 18 | `test_loan.py` (octroi, refus, dérogation, échéancier, retenue, anticipé, départ) | présent | 25 tests |
| 19 | `test_allowance.py` (chevauchement, prorata début/fin, manuelle prioritaire, % suit la version, forcée sans motif) | présent | 14 tests |
| 20 | noyau pur testé | présent | `lib/tests/test_loans.py` (27 cas), `test_allowances.py` (14 cas) |

## C2 — Traçabilité exigence → code → test

| Exigence | Code | Test |
|---|---|---|
| RG19 (prêts d'un salarié, échéances) | `employee_id` requis, `line_ids` | `test_sequence_and_schedule` |
| RG20 (2 ans, 40 % du net, plafond, sauf dérogation motivée) | `MinSeniority`, `MaxInstallmentRatio`, `MaxOutstanding`, `action_approve` | `test_refused_seniority`, `test_refused_installment_over_40_percent`, `test_refused_without_reference_payslip`, `test_refused_outstanding_over_company_cap`, `test_derogation_requires_reason_and_is_traced`, noyau `test_*_failure` |
| RG21 (une échéance, au plus un bulletin) | `payslip_id` Many2one ; exclusion des échéances déjà reprises ; contrôle à la validation | `test_installment_taken_by_one_payslip_only`, `test_withheld_at_validation_released_on_cancel`, `test_modified_loan_input_refused_at_validation` |
| RG28 (pas de chevauchement) | `_check_l10n_ga_overlap` | `test_overlap_refused`, `test_overlap_ignores_closed_and_deductions` |
| F1 (cycle de vie, report, anticipé, départ) | modèle, assistant, paie | `test_postpone`, `test_early_repayment_*`, `test_departure_*`, `test_loan_paid_after_last_installment`, `test_cancel_*` |
| F15 (modes, prorata, priorité manuelle, forcée imposable) | extension, `_l10n_ga_allowance_inputs`, `_l10n_ga_gain_lines` | `test_one_marked_input_per_allowance`, `test_prorata_*`, `test_manual_input_replaces_automatic`, `test_wage_percent_follows_version`, `test_quantity_times_rate`, `test_forced_taxable_*` |
| ADR-16 (ajustement daté, `record_payment` sans effet, retenues standard) | `record_payment` filtré, `l10n_ga_is_allowance` | `test_record_payment_without_effect`, `test_deduction_attachment_keeps_standard_behaviour`, `test_input_types` |
| Sprint 0 point 6 (`GA_LOAN` hors ajustements, créée sur le brouillon) | catalogue, `compute_sheet` | `test_loan_not_in_attachments`, `test_installment_on_payslip_of_the_period_only` |
| D-30 (retenue à la validation) | `action_payslip_done`, `_cancel`, `_draft` | `test_withheld_at_validation_released_on_cancel`, `test_released_when_back_to_draft` |
| D-31 (net de référence) | `_reference_net` | `test_refused_without_reference_payslip` |
| D-32 (quotité saisissable) | `seizable_portion`, `_l10n_ga_cap_departure_loan` | `test_departure_capped_by_seizable_portion`, `test_seizable_portion` (160 000 → 40 000), `test_seizable_brackets_from_yaml` |
| D-36 (forcée partielle) | `_l10n_ga_forced_shares`, figement regroupé par code | `test_forced_taxable_on_part_of_the_month` |
| Règle d'or 1 | YAML `prets` → 3 paramètres datés | `test_every_parameter_installed_for_gabon`, générateur `--check` |
| Règle d'or 6 (variables = entrées ; indemnités = lignes datées) | entrées marquées | tests F15 |
| Règle d'or 7 (exonérations par ligne) | `GainLine` scindée | `test_forced_taxable_loses_exemption` |
| Règle d'or 11 (multi-société) | `company_id`, `check_company`, règles | `test_multi_company_rule` |

## C3 — Chasse aux trous

| Contrôle | Résultat |
|---|---|
| `TODO|FIXME|XXX|HACK|NotImplementedError|pass$|...$` | 0 (interface `Spec` documentée sans méthode abstraite) |
| fichiers du manifeste absents / non déclarés | 0 / 0 |
| modèles sans accès / sans règle multi-société | 0 / 0 (assistant transitoire : sans règle) |
| champs de vue inexistants | 0 (installation) |
| nombres littéraux | aucun taux ; `PERCENT = 100` ; seuils en paramètres |
| `import odoo` dans le noyau | 0 |
| syntaxe pré-19 | 0 |
| libellés non traduisibles | 0 (`self.env._`) |
| méthodes publiques sans test | 0 |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | outillage 64 passés ; noyau **439** passés, couverture **100 %** |
| `make test MODULE=l10n_ga_hr_payroll` | base neuve : code 0, **108 tests**, 0 ERROR/CRITICAL |
| `make upgrade MODULE=l10n_ga_hr_payroll` | code 0, 108 tests, 0 ERROR/CRITICAL (avertissements : configuration du serveur, `pdfminer`) |
| installation puis désinstallation (base `test_ga_` supprimée ensuite) | `uninstalled`, 0 table, 0 colonne `l10n_ga_*`, 0 paramètre |
| `make i18n` | code 0 |

Corrigé pendant C4 : au départ, seules les échéances échues étaient reprises (le restant dû entier l'est désormais) ; un montant saisi en mode « % du salaire » bloquait le calcul (ignoré à la création) ; helper de test qui empêchait le calcul standard des entrées ; `_totals` des tests qui écrasait les lignes multiples d'un même code (Odoo 19 crée une ligne par entrée de même type, `E/hr_payroll/models/hr_payslip.py:1183-1212`) ; avertissements pylint anciens (return après `super`, `string` redondant, `Command` importé depuis `odoo.fields`).

## C5 — Recette chiffrée

| Cas | Attendu | Obtenu | Écart |
|---|---|---|---|
| échéancier 100 000 en 3 | 33 333 / 33 333 / 33 334 | idem | 0 |
| quotité saisissable, net 160 000 (base 05 §7) | 40 000 | 40 000 | 0 |
| anticipé hors paie 150 000 sur 3 × 100 000 | restent 100 000 + 50 000 | idem | 0 |
| anticipé sur bulletin 200 000 | `GA_LOAN` septembre −300 000, prêt soldé | idem | 0 |
| départ au 30/09, 3 × 100 000 | `GA_LOAN` −300 000 | idem | 0 |
| indemnité 30 000 à partir du 16/09 | 15 000 | 15 000 | 0 |
| revalorisation 30 000 → 60 000 au 16/09 | 15 000 + 30 000 | idem | 0 |
| 10 % du salaire, 400 000 puis 500 000 | 40 000 / 50 000 | idem | 0 |
| GA_RESP 60 000, moitié forcée imposable | exonéré 30 000 | 30 000 | 0 |
| F16 et profils 2.3 / 2.4 | inchangés | verts | 0 |

## Bloquants

Aucun.

## Questions pour Alex (non bloquantes)

1. **Barème de la quotité saisissable** (art. 729 CPC) : valeurs de 2012 (base 05 §7, « à actualiser »). Un barème plus récent est-il connu ? Il suffira d'ajouter une valeur datée au YAML.
2. **Démo** : `make demo MODULE=l10n_ga_hr_payroll` sur `odoo19` (redémarre le service), sur ton accord.

## Dette technique acceptée

| Élément | Justification | Résorption |
|---|---|---|
| Parts exonérées d'une rubrique à plusieurs lignes réparties au prorata des montants des lignes (pas par entrée forcée) | le total du bulletin et de la rubrique est exact ; les lignes ne portent pas l'entrée d'origine | si le bulletin PDF (2.7) doit détailler par ligne |
| Échéance d'un mois sans bulletin non reprise le mois suivant | prévisibilité ; report explicite (D-34) | contrôle F8 à l'étape 2.6 |
| Contrôles de lot « échéance > 40 % du net », « indemnité forcée sans motif » | blocage déjà à la saisie | chaîne F8, étape 2.6 |
| Décaissement du prêt et compte `pcg_4211` | comptabilité | étape 3 |
| Saisie manuelle d'un type d'ajustement effacée par le standard quand les dates du bulletin changent | comportement natif de `_compute_input_line_ids` | sans objet |
