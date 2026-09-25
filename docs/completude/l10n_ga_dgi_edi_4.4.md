# Complétude — `l10n_ga_dgi_edi`, étape 4.4 (DAS ID19 à ID22, « Contrôle DAS »)

Date : 25/09/2026 — plan `docs/plans/4.4.md` ; **go d'Alex « sans les classeurs »** (D-87) ; D-88 à D-94.

## Score

**16 / 17 éléments attendus présents et testés (94 %)** — le remplissage des gabarits officiels `.xlsm` (ID19 / ID21 / ID23 / ID26) reste à faire à réception de la V1 (D-07, D-87 : écart accepté par Alex). 89 tests Odoo verts sur base neuve et en mise à jour ; 300 tests verts avec la paie et la comptabilité ; installation sur base existante et désinstallation propres.

## C1 — Inventaire

| # | Élément (prompt 04 §4.4) | État | Fichier | Test |
|---|---|---|---|---|
| 1 | Type DAS (annuel, 30 avril N+1, cron J-10, pas à chaque bulletin) | présent | `data/l10n_ga_declaration_type_das_data.xml`, `prepare_on_payslip` | `test_type_and_preparation` |
| 2 | ID21 : détail salarié, colonnes (1) à (11) + non imposables | présent | `generators/das.py`, colonnes DAS du catalogue (`source_das_column`) | `test_columns_from_das_classification` |
| 3 | ID21 paginé (39 lignes / feuille, paramètre daté) | présent | `DasWorkbook._id21` | `test_workbook_and_pdf` (1 ligne / feuille forcée) |
| 4 | ID20 (tranches < / ≥ 1 000 000) | présent | cases `ID20_*` | `test_id20_tranches_and_id19` |
| 5 | ID19 (salariés > 80 000 / mois) | présent | `id19` du détail, feuille par salarié | `test_id20_tranches_and_id19`, `test_workbook_and_pdf` |
| 6 | ID22 : versements lus sur les quittances de l'année | présent | détails `PAID_*` | `test_id22_from_receipts` |
| 7 | Valeurs figées des bulletins et des lignes (F7, F16) | présent | `l10n_ga_tax_exempt`, identité figée du bulletin | `test_columns_from_das_classification` |
| 8 | Cumuls d'ouverture (F12) | présent | `opening_fields` des cases | `test_switch_year_with_opening` |
| 9 | Point 09-6 en option société (colonne (1) nette, base du classement) | présent | `res_company.py` | `test_columns_from_das_classification` (option brute) |
| 10 | Assistant `l10n_ga_das_wizard` | présent | `wizard/l10n_ga_das_wizard.py` | `test_type_and_preparation`, `test_check_screen` |
| 11 | Écran « Contrôle DAS » (liste partagée des anomalies) | présent | `l10n_ga_check_issue_action_das`, menu | `test_check_screen` |
| 12 | Contrôle total ID21 = Σ ID10 de l'année (par impôt, CFP avec l'ID28) | présent | `control_boxes` en données, `_reconciliation_issues` | `test_das_equals_sum_of_id10`, `test_missing_id10_and_mismatch` |
| 13 | Salarié sans NIF / CNSS | présent | `GA_DAS_NO_NIF`, contrôle commun | `test_employee_checks` |
| 14 | Codes emploi / niveau manquants | présent | `GA_DAS_NO_JOB_CODE` (avertissement, point 09-16) | `test_employee_checks` |
| 15 | Salarié sorti en cours d'année | présent | période, mois payés | `test_employee_leaving_during_year` |
| 16 | Rendu Excel et PDF (ID20, ID21, ID22, ID19) | présent | `DasWorkbook`, `report_das.xml` (A3 paysage) | `test_workbook_and_pdf` ; rendu PDF réel contrôlé |
| 17 | Remplissage des `.xlsm` officiels (Builder `openpyxl`, macros conservées) | **absent** (D-87) | le Builder `.xlsm` existe (4.1) ; gabarits V1 manquants | — |

## C2 — Traçabilité

| Exigence | Code | Test |
|---|---|---|
| Base 06 §3.1 (colonnes) | cases DAS + `das_column` du catalogue | `test_columns_from_das_classification` |
| Base 06 §3.2 (ID19 à ID22) | `DasWorkbook` | `test_workbook_and_pdf` |
| Base 06 §3.3 anomalie 1 (CFP exclue du total ID22) | (11) = (7) + (8) + (9) + (10) | `test_das_equals_sum_of_id10` |
| Base 06 §3.3 anomalie 2 (effectif par feuille) | ID22 : colonne « Salariés » | `test_workbook_and_pdf` |
| Base 06 §3.3 anomalie 9 (dates figées) | échéance calculée | `test_type_and_preparation` |
| Base 06 §4 (Σ ID10 = ID21 ; ID22 = retenues) | `_reconciliation_issues`, `_payment_issues` | `test_das_equals_sum_of_id10`, `test_id22_from_receipts` |
| Point 09-6 | options société | `test_columns_from_das_classification` |
| F12 | cumuls d'ouverture | `test_switch_year_with_opening` |
| RG13, RG14, RG15 | détails, instantané, bloquants | `test_workbook_and_pdf`, `test_employee_checks` |
| Règle d'or 1 | seuils et pagination en paramètres datés (YAML → `hr_rule_parameters_data.xml`) | `make test-core` (outil YAML), `test_workbook_and_pdf` |
| Règle d'or 13 | point 09-6 en option | idem |

## C3 — Chasse aux trous

Aucun `TODO` ni bouchon ; manifeste complet ; 1 nouveau modèle (assistant) avec ACL ; aucun nombre métier dans le générateur (seuils lus en paramètres ; 12 mois = calendrier) ; syntaxe 19 ; traductions régénérées (déclarations et paie).

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | 73 + 483 tests, couverture 100 % (paramètres DAS ajoutés au YAML) |
| `make test MODULE=l10n_ga_dgi_edi` | 89 tests, 0 échec |
| `make upgrade MODULE=l10n_ga_dgi_edi` | 89 tests, 0 échec |
| paie + comptabilité + déclarations | 300 tests, 0 échec |
| installation sur base existante / désinstallation | 5 types, 92 cases → `uninstalled` |

## C5 — Recette

DAS = Σ des 3 ID10 de janvier à mars (F16) pour TCS, IRPP, CFP, FNH : écart 0 ; colonne (1) = part imposable des rubriques « présence » − cotisations salariales ; bascule avec cumuls d'ouverture : rapprochement ID10 équilibré ; ID22 = 3 quittances.

## Bloquants et questions pour Alex

- **D-87** : gabarits `edi-annexe-ID19/21/23/26.xlsm` de la V1 (copie dans `/home/ubuntu/odoo/v1_l10n_ga_dgi_edi`) pour brancher le remplissage officiel.
- **D-90 / D-91** (point 09-6) : base de la moyenne et colonne (1) à confirmer avec le centre des impôts (options société en place).
- Nomenclature DGI des codes emploi / niveau (point 09-16) : champs libres, avertissement si vides.
- Rappels : D-74 (NIF sur les gabarits), D-83 (format des portails CNSS / CNAMGS).

## Dette technique acceptée

- Cumuls d'ouverture non ventilés par colonne (D-92) : reprise simplifiée signalée par un avertissement.
- Codes situation / sexe / nationalité imprimés en chiffres DGI (1 à 4).
