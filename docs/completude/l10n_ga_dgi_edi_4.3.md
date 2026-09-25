# Complétude — `l10n_ga_dgi_edi`, étape 4.3 (DTS CNSS et CNAMGS)

Date : 25/09/2026 — plan `docs/plans/4.3.md` (go anticipé, D-82 à D-86).

## Score

**16 / 16 éléments attendus présents et testés (100 %)** ; 75 tests Odoo verts sur base neuve et en mise à jour ; 286 tests verts avec la paie et la comptabilité installées ensemble ; installation sur base existante et désinstallation propres.

## C1 — Inventaire (par imprimé)

| # | Élément | État | Fichier | Test |
|---|---|---|---|---|
| 1 | DTS CNSS — type trimestriel, mois de paie, le 30 M+1, J-10, rapport | présent | `data/l10n_ga_declaration_type_dts_data.xml` | `test_types` |
| 2 | DTS CNSS — cases (en-tête, effectif, soumis, plafonné, SAL, PF, AT, AVID, total) | présent | idem | `test_full_quarter_cnss` |
| 3 | DTS CNSS — générateur, détail nominatif mensuel | présent | `models/generators/dts.py` | `test_full_quarter_cnss`, `test_entry_and_exit_during_quarter` |
| 4 | DTS CNAMGS — type, cases (soumis, plafonné, SAL, PAT, total), générateur | présent | idem | `test_full_quarter_cnamgs` |
| 5 | Assiette plafonnée par salarié et par mois | présent | bases figées `l10n_ga_base` | `test_ceilings` |
| 6 | Branches PF / AT / AVID | présent | cases `PF`, `AT`, `AVID` | `test_full_quarter_cnss` |
| 7 | Entrée / sortie en cours de trimestre | présent | payload (dates, mois à 0) | `test_entry_and_exit_during_quarter` |
| 8 | Plafond atteint ; plusieurs bulletins dans le mois | présent | `GA_DTS_CEILING` | `test_ceilings`, `test_two_payslips_same_month_over_ceiling` |
| 9 | Totaux DTS = Σ lignes CNSS / CNAMGS des bulletins | présent | cases sourcées ; `GA_DTS_TOTALS` | `test_full_quarter_*` |
| 10 | N° CNAMGS exigé pour la CNAMGS, n° CNSS pour la CNSS | présent | `GA_DECL_NO_CNAMGS`, `_requires_cnss_number` | `test_missing_numbers` |
| 11 | Rendu Excel (format documenté, colonnes nominatives) | présent | `_detail_columns`, `_render_xlsx` | `test_excel_and_pdf` |
| 12 | PDF récapitulatif (paysage, état nominatif) | présent | `report/report_dts.xml`, macro `report_declaration_nominative` | `test_excel_and_pdf` |
| 13 | Échéances trimestrielles, Observer | présent | type + Observer | `test_types`, `_dts()` (préparée à la validation) |
| 14 | Mois de paie, pas la date de paiement (D-82) | présent | `period_basis = period` | `test_payment_date_does_not_move_quarter` |
| 15 | Moteur : champ figé du bulletin, comptage, mensuel, plafond, trimestre (génériques, en données) | présent | `l10n_ga_declaration_box.py`, `declaration_generator.py` | tests DTS + non-régression ID10/ID28 |
| 16 | Traductions | présent | `i18n/fr.po` (363 entrées) | `make i18n` |

## C2 — Traçabilité

| Exigence | Code | Test |
|---|---|---|
| Base 03 §5 (état nominatif, 3 mois, cotisations) | `dts.py` | `test_full_quarter_cnss`, `test_excel_and_pdf` |
| Base 03 §1 (plafonds mensuels, SMIG) | assiette figée (`l10n_ga_social_base`, `l10n_ga_base`) | `test_ceilings` |
| Base 02 §3 (30/01, 30/04, 30/07, 30/10) | `due_months = 1`, `due_day = 30` | `test_types` |
| RG13 (détail justifie) | total nominatif = total dû | `test_entry_and_exit_during_quarter` |
| RG15 (bloquant) | numéros manquants | `test_missing_numbers` |
| Règle d'or 1 | plafonds lus par `ceiling_parameter` (données) | `test_two_payslips_same_month_over_ceiling` |
| Règle d'or 8 | valeurs figées des bulletins ; numéro figé, repli sur la version | `test_missing_numbers` |
| Règle d'or 10 | classeur neuf xlsxwriter, valeurs | `test_excel_and_pdf` |
| ADR-07 | 2 imprimés = données + un générateur | — |

## C3 — Chasse aux trous

Aucun `TODO` ni bouchon ; manifeste complet ; aucun nouveau modèle concret (ACL inchangées) ; aucun nombre littéral métier ; syntaxe 19 ; traductions régénérées.

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | 73 + 483 tests, couverture 100 % |
| `make test MODULE=l10n_ga_dgi_edi` | 75 tests, 0 échec |
| `make upgrade MODULE=l10n_ga_dgi_edi` | 75 tests, 0 échec |
| paie + comptabilité + déclarations | 286 tests, 0 échec |
| installation sur base existante / désinstallation | 4 types, 62 cases → `uninstalled`, 0 modèle restant |

## C5 — Recette chiffrée (F16, T3 2026, 3 bulletins)

| Case | Attendu (bulletins) | Déclaré | Écart |
|---|---|---|---|
| CNSS salaires soumis / plafonnés | 1 665 000 / 1 665 000 | idem | 0 |
| CNSS SAL (5 %) | 83 250 | 83 250 | 0 |
| CNSS PF + AT + AVID (18 %) | 299 700 | 299 700 | 0 |
| CNAMGS SAL (2 %) / PAT (4,1 %) | 33 300 / 68 265 | idem | 0 |
| Cadre 2 000 000 : base CNSS / CNAMGS | 1 500 000 / 2 000 000 | idem | 0 |
| Dirigeant 3 000 000 : base CNAMGS | 2 500 000 | idem | 0 |

## Bloquants et questions pour Alex

- **D-83** : colonnes exactes attendues par les portails CNSS et CNAMGS (un export ou un modèle suffit) ; le classeur actuel suit la base 03 §5.
- Rappels : D-74 (cellule du NIF), D-07 avant 4.4.

## Dette technique acceptée

- Le détail nominatif est recalculé à partir des mêmes faits pour les contrôles (deux passes) : volumes trimestriels faibles.
- La date de sortie est lue sur la version du jour (non figée sur le bulletin) : elle n'entre dans aucun montant.
