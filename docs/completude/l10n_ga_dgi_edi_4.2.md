# Complétude — `l10n_ga_dgi_edi`, étape 4.2 (ID10, ID28, quittances multiples)

Date : 25/09/2026 — plan `docs/plans/4.2.md` (go anticipé, D-74 à D-81).

## Score

**20 / 20 éléments attendus présents et testés (100 %)** ; 66 tests Odoo verts sur base neuve et en mise à jour ; 277 tests verts avec la paie et la comptabilité installées ensemble ; installation sur base existante et désinstallation propres.

## C1 — Inventaire (par imprimé : type, cases, générateur, Excel, PDF, contrôles, tests)

| # | Élément | État | Fichier | Test |
|---|---|---|---|---|
| 1 | ID10 — type (mensuel, date de paiement, le 15 M+1, J-10, gabarit, rapport) | présent | `data/l10n_ga_declaration_type_data.xml` | `test_id10.test_type_data` |
| 2 | ID10 — 22 cases avec cellules du gabarit (en-tête, cadre 2, cadre 3) | présent | idem | `test_template_filled_with_values` |
| 3 | ID10 — générateur (`_read_group`, bulletins validés/payés, `l10n_ga_payment_date`) | présent | `models/generators/id10.py`, `declaration_generator.py` | `test_f16_single_payslip`, `test_sum_of_paid_payslips_only` |
| 4 | ID10 — rendu Excel (gabarit officiel, valeurs, formules remplacées) | présent | `static/templates/ID10.xlsx` | `test_template_filled_with_values` |
| 5 | ID10 — rendu PDF QWeb | présent | `report/report_id10.xml` | idem (contenu du rendu) |
| 6 | ID10 — contrôles (communs + arrondi CFP) | présent | `generators/id10.py` | `test_f16_single_payslip` (aucune anomalie), `test_checks` |
| 7 | ID10 — détails par salarié | présent | générateur générique | `test_f16_single_payslip`, `test_multi_company` |
| 8 | Décembre payé en janvier → ID10 de janvier | présent | base « date de paiement » | `test_december_paid_in_january` |
| 9 | Changement FNH au 17/07/2026 | présent | valeurs figées des bulletins | `test_fnh_rate_change_17_july_2026` |
| 10 | Multi-société | présent | domaine société | `test_multi_company` |
| 11 | Option société « CFP sur ID28 » | présent | `_blank_sections`, `_applies` | `test_cfp_on_id28_leaves_frame_blank`, `test_id28` |
| 12 | ID28 — type, 18 cases, générateur | présent | `data/…`, `generators/id28.py` | `test_cfp_declared_once_on_id28` |
| 13 | ID28 — Excel et PDF | présent | `static/templates/ID28.xlsx`, `report/report_id28.xml` | idem |
| 14 | ID28 — contrôle « CFP déjà sur l'ID10 » (bloquant) | présent | `generators/id28.py` | `test_manual_id28_blocked_when_cfp_on_id10` |
| 15 | `l10n_ga.declaration.payment` (plusieurs quittances, nature RS / FNH / CFP / autre, pièces jointes) | présent | `models/l10n_ga_declaration_payment.py` | `test_payments` |
| 16 | « payée » quand Σ quittances couvre le total (RG16) | présent | `_l10n_ga_update_payment_state` | `test_two_receipts_make_it_paid`, `test_paid_before_filing` |
| 17 | Paiement partiel ; sur-paiement signalé | présent | idem (`GA_DECL_OVERPAID`) | `test_partial_payment_stays_filed`, `test_overpayment_flagged` |
| 18 | Onglet « Quittances », menu, sécurité (déclarant seul), règle multi-société | présent | vues, `security/*` | `test_payment_rules`, `test_multi_company_rule` |
| 19 | Générateur générique enrichi (codes signés, catégories, mesures, sommes, paramètres, cadres) — codes en données uniquement | présent | `declaration_generator.py`, `l10n_ga_declaration_box.py` | `test_id10`, `test_generator_registry` |
| 20 | Cases non renseignées (cadre vide) dans l'instantané et les rendus | présent | `value_blank` | `test_cfp_on_id28_leaves_frame_blank` |

## C2 — Traçabilité

| Exigence | Code | Test |
|---|---|---|
| RG16 (quittances, payée) | payment + `_l10n_ga_update_payment_state` | `test_payments` |
| F11 (quittances multiples) | `payment_ids` | `test_two_receipts_make_it_paid` |
| ADR-06 (figée) | quittances hors instantané ; empreinte inchangée | `test_template_filled_with_values` (après validation) |
| ADR-07 (imprimé = données + générateur) | types et cases en XML, 2 générateurs de 20 lignes | `test_id10`, `test_id28` |
| ADR-08 (pas de XML) | Excel + QWeb | — |
| Règle d'or 1 (aucun taux en dur) | taux CFP = `parameter_code`, codes de rubriques en données (prompt 04 : jamais en dur) | `test_f16_single_payslip` (R55 lu) |
| Règle d'or 8 (lue sur les valeurs figées) | bases `l10n_ga_base`, parts `l10n_ga_social_excluded` | `test_cfp_ceiling_per_employee` |
| Règle d'or 10 (valeurs, jamais de formules) | `XlsmTemplateRenderer` | `test_template_filled_with_values` (aucun `<f>`) |
| Règle d'or 11 (multi-société) | domaines, ir.rule quittance | `test_multi_company`, `test_multi_company_rule` |
| Règle d'or 13 (point non tranché = option) | CFP ID10/ID28 (option société existante) | `test_id28` |
| Base 06 §2 « jamais la CFP deux fois » | D-76 | `test_cfp_declared_once_on_id28` |

## C3 — Chasse aux trous

Aucun `TODO`/`FIXME`, aucun bouchon ; fichiers du manifeste présents et tous déclarés ; 6 modèles concrets, 10 lignes d'ACL, 4 règles multi-société ; aucun nombre littéral métier dans les générateurs (seulement `0.0`) ; syntaxe 19 respectée ; `i18n` régénéré (325 entrées).

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | 73 + 483 tests, couverture du noyau 100 % |
| `make test MODULE=l10n_ga_dgi_edi` | 66 tests, 0 échec, 0 ligne ERROR |
| `make upgrade MODULE=l10n_ga_dgi_edi` | 66 tests, 0 échec, 0 ligne ERROR |
| paie + comptabilité + déclarations | 277 tests, 0 échec (l'Observer prépare l'ID10 à chaque bulletin validé des tests de paie) |
| installation sur base existante / désinstallation | types `ID10`, `ID28`, 40 cases → `uninstalled`, 0 modèle restant |

## C5 — Recette chiffrée (F16, septembre 2026)

| Case ID10 | Attendu (oracle de la paie) | Déclaré | Écart |
|---|---|---|---|
| P40 IRPP | 23 195 | 23 195 | 0 |
| P41 TCS | 13 058 | 13 058 | 0 |
| P42 FNH (3 %) | 16 650 | 16 650 | 0 |
| P43 total | 52 903 | 52 903 | 0 |
| R49 + R50 + R53 | 555 000 (assiette sociale) | 555 000 | 0 |
| R54 base / R55 taux / R56 CFP | 555 000 / 0,5 % / 2 775 | idem | 0 |
| Juin 2026 FNH (2 %) | 11 100 | 11 100 | 0 |

## Bloquants et questions pour Alex

- **D-74** : cellule du NIF (`E17` sur l'ID10, `D17` sur l'ID28) supposée — à confirmer sur un imprimé rempli.
- Rappels : code rubrique `V39` (table DGI, D-81) ; usage ID10 seul ou ID10 + ID28 par le centre des impôts (base 06 §2 🔴) ; D-07 avant 4.4.

## Dette technique acceptée

- L'option CFP (ID10 / ID28) et l'assiette CFP (sociale / brute) sont lues à la date du calcul de la déclaration : sans effet sur les montants, qui viennent des lignes figées des bulletins.
- Le passage en « payée » reste global (total dû) ; le rapprochement par nature de quittance (RS / FNH / CFP) sera exploité par la grille ID22 de la DAS (4.4).
