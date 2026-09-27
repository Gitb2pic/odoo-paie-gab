# Complétude C-3 — module `l10n_ga_dgi_edi` (étapes 4.1 à 4.4)

Date : 25/09/2026 — prompt `99_completude.md` ; « go pour la C-3 ». Étape 4.5 (migration V1) **hors complétude** : bloquée par D-07 (code et base V1 absents), reportée par Alex.

## Score

**Étapes 4.1 à 4.4 : 77 / 79 éléments attendus présents et testés (97 %).** Manques restants, tous bloqués par la V1 (D-07 / D-87) : gabarits `.xlsm` de la DAS (ID19 / ID21) et, pour 4.5, scripts `migrations/19.0.2.0.0` et `test_v1_ported.py`. 95 tests du module sur base neuve et en mise à jour ; **337 tests** verts avec les quatre modules Gabon.

## Manques relevés et corrigés

| # | Manque | Correction | Test |
|---|---|---|---|
| 1 | Nombres en dur dans les générateurs (12 mois, noms de feuille 25 / 28 caractères, lignes en gras de l'ID19 par index) | constantes `MONTHS_PER_YEAR`, `SHEET_NAME_MAX`, lignes en gras calculées depuis `ID19_GAINS` | `test_das` (non-régression) |
| 2 | Convertisseur classeur → PDF (`xlsx_html`) sans test unitaire des formats | pourcentages, colonnes / lignes masquées, fusions, gras et couleur, fond de cellule, dates, formules jamais affichées, en-tête répété, débordement borné, feuilles masquées, une feuille par page | `test_excel_to_html_formats`, `test_sheets_on_separate_pages` |
| 3 | Listes des gabarits (`rows`, `copy_sheet`, `remove_sheet`, retrait des formules) testées seulement via le module comptable | tests directs dans le moteur (projet VBA conservé) | `test_template_rows_sheets_and_formulas` |
| 4 | Case de nature « date » non testée (stockage, rendu Excel) | générateur factice + classeur neuf | `test_date_box_and_builder` |
| 5 | Observer à l'**annulation** d'un bulletin non testé | bulletin annulé → déclaration recalculée | `test_observer_on_payslip_cancel` |
| 6 | Bouton « Corriger » d'une anomalie de déclaration non testé | ouvre le salarié à corriger | `test_issue_opens_record_to_fix` |

## Inventaire par imprimé

| Imprimé | Type | Cases | Générateur | Excel | PDF | Contrôles | Tests |
|---|---|---|---|---|---|---|---|
| Moteur (4.1) | ✔ | ✔ | registre + interface + générique | ✔ xlsx / xlsm | ✔ rendu du classeur | ✔ 4 communs | ✔ 50 |
| ID10 | ✔ mensuel, 15 M+1 | ✔ 22 (cellules) | ✔ | ✔ gabarit officiel | ✔ | ✔ + arrondi CFP | ✔ 9 |
| ID28 | ✔ | ✔ 18 | ✔ | ✔ gabarit officiel | ✔ | ✔ CFP déjà sur l'ID10 | ✔ 3 |
| Quittances (F11) | — | — | — | — | ✔ | ✔ sur-paiement | ✔ 7 |
| DTS CNSS / CNAMGS | ✔ trimestriels, 30 M+1 | ✔ 12 / 10 | ✔ | ✔ classeur mis en forme | ✔ paysage | ✔ plafond, totaux, numéros | ✔ 9 |
| DAS ID19 à ID22 | ✔ annuel, 30/04 | ✔ 32 | ✔ | ✔ classeur neuf (`.xlsm` V1 absents) | ✔ A3 | ✔ Σ ID10, NIF, codes, versements | ✔ 11 |

## Chasse aux trous (C3)

| Vérification | Résultat |
|---|---|
| TODO / bouchons | aucun ; `NotImplementedError` seulement dans les interfaces abstraites documentées (patrons 4, 8, 9) |
| Manifeste ↔ fichiers | complet, aucun XML / CSV non déclaré |
| Droits / règles | 8 modèles concrets (dont l'assistant) avec ACL ; règles multi-société sur déclaration, ligne, détail, quittance |
| Champs des vues | contrôle `view-fields` (FIX 02) vert ; vues validées à l'installation |
| Nombres en dur | aucun taux ni seuil (paramètres datés, données des cases) ; constantes de calendrier nommées |
| Syntaxe pré-19 | aucune |
| Messages | tous traduisibles (`self.env._`) ; `i18n` régénéré |
| Points 🔒 | sprint 0 points 3 et 13 (états, validation) confirmés |
| Hypothèses 09 | points 6 (options société DAS), 16 (codes emploi libres, avertissement) |
| Architecture `06` §1 | écarts justifiés : Observer sur `hr_payslip.py` (ADR-19, et non `hr_payslip_run.py`) ; contrôles dans `checks.py` ; un rapport PDF commun rendu depuis le classeur (demande d'Alex) au lieu de `report_id10.xml`… séparés ; `test_v1_ported.py` → 4.5 |

## Exécution (C4)

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | 79 + 490 tests, couverture du noyau 100 % |
| `make test MODULE=l10n_ga_dgi_edi` | 95 tests, 0 échec |
| `make upgrade MODULE=l10n_ga_dgi_edi` | 95 tests, 0 échec |
| quatre modules Gabon ensemble | 337 tests, 0 échec |

## Recette (C5)

ID10 = Σ bulletins payés du mois (F16 : IRPP 23 195, TCS 13 058, FNH 16 650, total 52 903, CFP 2 775) ; DAS = Σ ID10 de l'année (TCS, IRPP, CFP, FNH) ; DTS = Σ cotisations du trimestre (CNSS 83 250 + 299 700, CNAMGS 33 300 + 68 265) : **écart 0**.

## Bloquants et questions pour Alex

- **D-07 / D-87** : V1 (`/home/ubuntu/odoo/v1_l10n_ga_dgi_edi`) pour la 4.5 et les `.xlsm` de la DAS.
- **D-74** (cellule du NIF), **D-83** (format des portails CNSS / CNAMGS), **D-90 / D-91** (point 09-6).

## Dette acceptée

- Bulletins validés avant le FIX 01 : réimpression sans base / taux de la ligne de base (rappel).
- Cumuls d'ouverture non ventilés par colonne DAS (D-92).
