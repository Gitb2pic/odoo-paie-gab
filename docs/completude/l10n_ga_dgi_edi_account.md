# Complétude — `l10n_ga_dgi_edi_account`, étape 5 (périmètre V1.0)

Date : 25/09/2026 — plan `docs/plans/5.md` ; « go pour la 5 sans la 4.5 » (Alex) ; D-95 à D-103.

## Score

**22 / 23 éléments attendus présents et testés (96 %)** — seul manque : gabarits `.xlsm` des annexes ID23 / ID26 de la V1 (D-87, D-99). 16 tests du module sur base neuve et en mise à jour ; **316 tests verts** avec paie, comptabilité de paie et déclarations installées ensemble ; installation sur une société déjà équipée du plan `ga` (retenues chargées par le `post_init_hook`) et désinstallation propres. **Aucun élément V2.0** (CA01, ID30, ID09, ID31, IS, patente, CFU) : vérifié par recherche.

## C1 — Inventaire (par imprimé : type, cases, générateur, rendu, contrôles, tests)

| # | Élément | État | Fichier | Test |
|---|---|---|---|---|
| 1 | Tiers : catégorie A / B / C / prestations / loyers, résident, zone CEMAC, assujetti TVA | présent | `models/res_partner.py` | `test_partner_classification` |
| 2 | Position fiscale automatique selon résidence et assujettissement | présent | positions `l10n_ga_fp_ras_*`, `_l10n_ga_apply_withholding_position` | `test_fiscal_position_follows_classification` |
| 3 | Taxes `l10n_ga_ras_095` / `l10n_ga_ras_20` par société, au paiement (`l10n_account_withholding_tax`), taux en données | présent | `data/template/*.csv`, `account_chart_template.py` | `test_taxes_loaded_on_ga_chart` |
| 4 | Sociétés déjà équipées : chargement idempotent, séquences de pièces de retenue | présent | `_post_init_hook`, `_l10n_ga_load_withholding` | `test_taxes_loaded_on_ga_chart`, installation réelle |
| 5 | Retenue ajoutée aux lignes de facture fournisseur | présent | `account_move_line._get_computed_taxes` | `test_bill_lines_get_withholding` |
| 6 | Anti-double retenue (contrainte) | présent | `check_withholding` (lignes de facture, lignes de retenue) | `test_no_double_withholding` |
| 7 | ID18 : type, 13 cases (en-tête aux cellules du gabarit), générateur, détails avec `move_line_ids` | présent | `generators/withholding.py`, données | `test_id18_full_payment` |
| 8 | ID18 : paiement partiel, deux paiements, avoir | présent | lignes de retenue des paiements, signe | `test_partial_and_two_payments`, `test_refund` |
| 9 | ID18 : gabarit officiel rempli (bordereau, feuillets supplémentaires, aucune formule) | présent | `_fill_template` | `test_template_filled` ; PDF réel contrôlé |
| 10 | ID27 : type, cases, générateur, gabarit | présent | idem | `test_id27_non_resident_only_20` |
| 11 | Non-résident → 20 % seul | présent | classement + contrainte | `test_id27_non_resident_only_20`, `test_no_double_withholding` |
| 12 | ID23 (salarié / non salarié), sommes versées | présent | `generators/fees.py` | `test_id23_employee_and_partial_payment` |
| 13 | ID24 (CEMAC / hors CEMAC), retenues | présent | idem | `test_id24_sections` |
| 14 | ID26, cohérence ID26 ↔ Σ ID18 | présent | `_monthly_issues` | `test_id26_matches_id18` |
| 15 | Rendus Excel et PDF des annexes | présent | `_render_workbook`, `action_report_das_annex` | `test_annual_workbook` ; PDF réel contrôlé |
| 16 | Contrôle bénéficiaire non classé | présent | `GA_RAS_UNCLASSIFIED` | `test_checks` |
| 17 | Contrôle NIF manquant (résidents) | présent | `GA_RAS_NO_NIF` | `test_checks` |
| 18 | Contrôle retenue absente sur fournisseur classé | présent | `GA_RAS_MISSING` | `test_checks` |
| 19 | Contrôle double retenue | présent | `GA_RAS_DOUBLE` | contrainte + contrôle (le cumul est bloqué dès la saisie) |
| 20 | Multi-société | présent | société des paiements, positions par société | `test_multi_company` |
| 21 | Observer paiement → ID18 / ID27 | présent | `account_payment.action_post` | `test_id18_full_payment` |
| 22 | `move_line_ids` du détail (D-73) | présent | `l10n_ga_declaration_detail.py` | `test_id18_full_payment` |
| 23 | Gabarits `.xlsm` des annexes ID23 / ID26 de la V1 | **absent** (D-87) | — | — |

## C2 — Traçabilité

| Exigence | Code | Test |
|---|---|---|
| RG27 (classement, non-résident 20 % seul) | `res_partner.py`, `check_withholding` | `test_partner_classification`, `test_no_double_withholding` |
| F9 (DAS et retenues dès la V1) | 5 générateurs | tests ID18 / ID27 / ID23 / ID24 / ID26 |
| ADR-09 (lu dans la comptabilité, pas recalculé) | paiements et leurs lignes de retenue | `test_partial_and_two_payments` |
| ADR-13 (périmètre V1.0) | aucun élément V2.0 | C3 |
| Sprint 0 point 7 (multi-paiements, avoirs) | `payments.py` | `test_partial_and_two_payments`, `test_refund` |
| Point 09-7 (20 % / 25 %) | taux sur la taxe, modifiable | `test_taxes_loaded_on_ga_chart` |
| Règle d'or 10 (valeurs, jamais de formules) | `_strip_formulas`, zones vidées | `test_template_filled` |
| Règle d'or 11 (multi-société) | `company_id` des paiements, positions par société | `test_multi_company` |
| Règle d'or 14 (dépendances) | dépend des déclarations, de `l10n_ga` et de la retenue au paiement | manifeste |

## C3 — Chasse aux trous

Aucun `TODO` ni bouchon (une interface abstraite documentée) ; manifeste complet ; aucun nouveau modèle (champs sur modèles standard) ; taux uniquement sur les taxes (données) ; aucun élément V2.0 ; traductions générées (103 entrées).

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | 73 + 483 tests, couverture 100 % |
| `make test MODULE=l10n_ga_dgi_edi_account` | 16 tests, 0 échec |
| `make upgrade MODULE=l10n_ga_dgi_edi_account` | 16 tests, 0 échec |
| `make test MODULE=l10n_ga_dgi_edi` | 89 tests, 0 échec (moteur étendu : `_fill_template`, valeurs supplémentaires des détails, formules retirées des gabarits) |
| quatre modules ensemble | 316 tests, 0 échec |
| installation sur société existante / désinstallation | 2 retenues, 2 positions, séquences → `uninstalled`, champs retirés |

## C5 — Recette

ID18 : 100 000 → retenue 9 500 ; 120 000 + 80 000 → 19 000 ; facture 100 000 − avoir 20 000 → 7 600 ; ID27 : 200 000 → 40 000 ; ID26 = Σ ID18 (14 250) ; ID24 : 200 000 hors CEMAC + 100 000 CEMAC → 60 000.

## Constat important (Odoo 19)

Un paiement dont le moyen n'a pas de compte d'attente reste « en cours » **sans écriture** jusqu'au rapprochement bancaire (la facture reste « en cours de paiement »). Les déclarations lisent donc les **lignes de retenue des paiements** et leurs factures, pas les écritures (D-97) ; l'écriture est jointe au détail dès qu'elle existe.

## Bloquants et questions pour Alex

- **D-103** : taux des non-résidents 20 % (modèle DGI) ou 25 % (PwC 2026) — modifiable sur la taxe.
- **D-87** : gabarits `.xlsm` de la V1 pour les annexes.
- Cellule du NIF (D-74) : en D16 sur l'ID18 / ID27, à confirmer.

## Dette technique acceptée

- Une facture soldée par un avoir sans paiement n'entre pas dans les sommes versées (rare ; documenté).
- Plan des associations `ga_syscebnl` : pas de retenues chargées (compte 4478 absent, cf. D-62).
