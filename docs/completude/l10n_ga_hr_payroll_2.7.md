# Complétude — `l10n_ga_hr_payroll`, étape 2.7 (rapports : bulletin figé, livre de paie, virements, billetage)

Date : 24/09/2026 — plan : `docs/plans/2.7.md` (« go avec tes recommandations » donné d'avance ; P1 à P7 → D-47 à D-53).

## Score

**16 / 16 éléments attendus présents et testés = 100 %.** Aucun bloquant. Une décision à confirmer par Alex : D-47 (mentions du bulletin, point 19 du fichier 09).

## C1 — Inventaire attendu / réel

| # | Élément attendu (prompt 2.7, F2, F7, F13, RG24, patron 9) | État | Emplacement |
|---|---|---|---|
| 1 | `report/report_payslip_ga.xml` : bulletin PDF QWeb | présent | action `action_report_payslip_ga`, gabarits `report_payslip_ga` et `_lang` |
| 2 | ne lit que les champs figés et les lignes (jamais la fiche du jour) | présent | `_l10n_ga_report_data()` (champs figés si validé), `_l10n_ga_report_lines()` (lignes stockées) ; identité figée à la validation (D-48) |
| 3 | mentions légales gabonaises | présent | identités employeur / salarié, période, paiement, temps, rubriques, bases, plafonds, cumuls, reliquat (D-47, à confirmer) |
| 4 | cumuls annuels, parts, bases | présent | tableaux « Bases du mois », « Cumuls de l'année », parts et situation |
| 5 | rapport utilisé par le standard (impression, PDF joint) | présent | `report_id` de la structure « Gabon — Employé » → `_get_pdf_reports` |
| 6 | livre de paie Excel (une ligne par bulletin, une colonne par rubrique, totaux) | présent | assistant `l10n_ga.payroll.report`, feuille « Livre de paie » (rubriques ayant un montant, D-50) |
| 7 | état des charges (CNSS par branche, CNAMGS, FNH, CFP, IRPP, TCS) | présent | feuille « État des charges » : parts salariale / patronale, sous-totaux par catégorie |
| 8 | rapprochement 43x/44x si la compta est installée | reporté (tracé) | étape 3 (D-51, règle d'or 14) — non compté comme manque de l'étape |
| 9 | état des virements par banque (une feuille par banque, `primary_bank_account_id`) | présent | compte figé sur le bulletin ; feuilles « Chèques », « Sans compte » (D-52) |
| 10 | état de billetage des paies en espèces | présent | coupures = paramètre daté, reste en pièces, totaux par coupure |
| 11 | `constant_memory` pour les gros volumes | présent | `report/xlsx_renderer.py` (`XlsxRenderer`, patron 9) |
| 12 | valeurs, jamais de formules (règle d'or 10) | présent | totaux calculés en Python ; test `assertNoFormula` |
| 13 | menus et actions | présent | Paie → Rapports → États de paie (Gabon) ; bouton « États de paie » sur le lot clos |
| 14 | droits | présent | accès assistant (paie) |
| 15 | test : bulletin validé, fiche modifiée, rendu identique | présent | `test_validated_payslip_reprinted_identically` |
| 16 | tests : livre (totaux = lignes), billetage (coupures = `GA_NET_PAY` espèces) | présent | `test_payroll_book_totals_equal_lines`, `test_cash_breakdown_sum_equals_cash_net_pay` |

## C2 — Traçabilité

| Exigence | Code | Test |
|---|---|---|
| F7 / RG24 (bulletin figé) | identité figée, `_l10n_ga_report_data` | `test_validated_payslip_reprinted_identically` (nom, emploi, n° CNSS, enfants, matricule, salaire, mode de paiement, compte, NIF employeur, plafond CNSS modifiés), `test_frozen_identity_and_report_data` |
| brouillon | mention « non validé », calcul du jour | `test_draft_marked_not_validated_and_reads_current_file`, `test_draft_without_lines_prints_identity` |
| rapport de la structure | `report_id` | `test_structure_uses_gabon_report`, `test_pdf_pipeline` |
| rubriques classées (gains, retenues, patronal, net à payer, avantages) | `_l10n_ga_report_lines` | `test_report_lines_classified`, `test_benefit_in_kind_line` |
| F13 livre de paie | `_render_book` | `test_payroll_book_totals_equal_lines`, `test_selection_by_period_and_company` |
| F13 état des charges | `_render_charges` | `test_charges_statement` |
| F2 virements | `_render_transfer` | `test_transfers_one_sheet_per_bank`, `test_transfers_use_frozen_account` |
| F2 billetage | `_render_cash` + noyau `cash_breakdown` | `test_cash_breakdown_sum_equals_cash_net_pay` |
| patron 9 / règle d'or 10 | `XlsxRenderer` | `test_renderer_sheet_names_and_values`, `assertNoFormula` sur les 3 états |
| D-49 (sélection) | `_slips` | `test_selection_by_period_and_company`, `test_period_required` |
| règle d'or 11 | `company_id` de l'assistant, `check_company` | `test_selection_by_period_and_company` (autre société : aucun bulletin) |

## C3 — Chasse aux trous

| Contrôle | Résultat |
|---|---|
| `TODO`, `FIXME`, `pass`, `...`, `NotImplementedError` | 0 nouveau (interface abstraite du patron 8 déjà documentée) |
| fichiers du manifeste absents / non déclarés | 0 / 0 |
| modèles sans accès / sans règle multi-société | 0 / 0 (assistant transitoire) |
| champs de vue ou de gabarit inexistants | 0 (installation, mise à jour, rendu testé) |
| nombres littéraux | largeur de colonne et format en constantes nommées ; coupures en paramètre daté |
| syntaxe pré-19 | 0 |
| libellés non traduisibles | 0 ; `.pot` / `fr.po` régénérés |
| méthodes publiques sans test | 0 |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | outillage 65 passés ; noyau 466 passés, couverture 100 % |
| `make test MODULE=l10n_ga_hr_payroll` | base neuve : code 0, **174 tests**, 0 ERROR/CRITICAL |
| `make upgrade MODULE=l10n_ga_hr_payroll` | code 0, 174 tests, 0 ERROR/CRITICAL (avertissements : configuration du serveur, `pdfminer`) |
| installation puis désinstallation (base `test_ga_` supprimée) | `uninstalled`, 0 table, 0 colonne `l10n_ga_*`, 0 paramètre, 0 rapport `l10n_ga*` |
| `make i18n` | code 0 |

Corrigé pendant C4 : attribut de test `run` masquant `TestCase.run` ; `ValidationError` pour les contraintes de l'assistant ; le rendu PDF réel en test (`force_report_rendering`) bloque — wkhtmltopdf attend les ressources du serveur de test, occupé par le test : lancement interrompu, base de test supprimée, test remplacé par la chaîne PDF standard (HTML en mode test, comme les tests Odoo).

## C5 — Recette chiffrée

| Cas | Attendu | Obtenu | Écart |
|---|---|---|---|
| livre de paie d'un lot de 6 bulletins | total de chaque colonne = somme des lignes = somme des `hr.payslip.line` | idem | 0 |
| état des charges | parts salariale / patronale = lignes `GA_CNSS_SAL`, `GA_CNSS_PF`… ; total = salarial + patronal | idem | 0 |
| virements (BGFI, UBA, chèque, sans compte) | somme des feuilles = `GA_NET_PAY` hors espèces | idem | 0 |
| billetage (401 237 et 277 777, arrondi 500) | Σ coupures × valeur + reste = Σ `GA_NET_PAY` espèces ; reste 0 | idem | 0 |
| bulletin réimprimé après modification de la fiche et d'un paramètre | HTML identique | identique | 0 |
| F16 et profils 2.3 à 2.6 | inchangés | verts | 0 |

## Bloquants et questions pour Alex

- **D-47 à confirmer** : liste des mentions obligatoires du bulletin (aucune liste dans la base de connaissance ; point 19 du fichier 09, à valider auprès de l'inspection du travail ou du cabinet).

## Dette technique acceptée

- En-tête `web.external_layout` (logo, adresse de la société) lu sur la société du jour, comme tous les rapports Odoo ; les identifiants fiscaux employeur imprimés dans le corps sont figés (D-48).
- Rendu PDF binaire non exécuté en test automatique (limite wkhtmltopdf / serveur de test) ; le HTML transmis à wkhtmltopdf est testé.
- Rapprochement comptable de l'état des charges : étape 3 (D-51).
