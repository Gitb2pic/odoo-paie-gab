# Complétude — dépôt complet (4 modules)

27/09/2026. Périmètre : `l10n_ga_hr_payroll`, `l10n_ga_hr_payroll_account`, `l10n_ga_dgi_edi`,
`l10n_ga_dgi_edi_account` (module de reprise `l10n_ga_hr_payroll_migration` abandonné, D-112 / ADR-21).
Prompt : `prompts/99_completude.md`, mode « dépôt complet ».

**Score : 100 % des éléments attendus présents et testés** — inventaires détaillés par module dans
`l10n_ga_hr_payroll_C-1.md`, `l10n_ga_hr_payroll_account_C-2.md`, `l10n_ga_dgi_edi_C-3.md`,
`l10n_ga_dgi_edi_account_C-4.md`, complétés depuis par FIX 01 à FIX 05 (rapports et plans correspondants).
Les deux manques restants de C-3 / C-4 (gabarits `.xlsm` de la V1, migration V1) sont soldés : `.xlsm`
branchés (FIX 05, D-87), migration V1 abandonnée (D-112).

## 1. Chasse aux trous (C3), sur les 4 modules

| Vérification | Résultat |
|---|---|
| `TODO / FIXME / XXX / HACK`, bouchons | aucun ; 10 `NotImplementedError` = interfaces abstraites documentées (patrons 4, 8, 9) |
| Manifeste ↔ fichiers | tous les fichiers déclarés existent ; non déclarés justifiés : `catalogue_rubriques_ga.csv` (source du générateur de règles), `data/template/*.csv` (plan comptable « ga », chargés par le modèle de plan) |
| Droits | 17 modèles, tous avec ACL ; règles multi-société sur tous les modèles à `company_id` ; règles de groupe comptables (FIX 03) |
| Syntaxe pré-19 (`_sql_constraints`, `attrs=`, `<tree`) | aucune |
| Champs `l10n_ga_*` des vues | `tools/check_view_fields.py` (lint) : OK |
| Imports `odoo` dans `ga_fiscal_core` | aucun (test AST + lint) |
| Messages non traduisibles | aucun (2 jointures de messages déjà traduits) |
| Paramètres : code ↔ YAML ↔ XML | 63 paramètres, table unique `param_codes.py`, `--check` OK ; 3 définis non lus par le code : `l10n_ga_cash_rounding_default` (lu via constante, défaut de l'option société), `l10n_ga_rmm_amount` et `l10n_ga_isr_resignation_ratio` (valeurs de référence du YAML ; ISR démission = rubrique imposable à 100 %, sans groupe) — dette acceptée |
| Catalogue : traitement social, fiscal, compte | 80 rubriques ; toutes traitées ; `GA_ROUND_PREV`, `GA_ROUND`, `GA_NET_PAY` « sans écriture » justifiées (D-44, tests C-2) |
| Types de déclaration : cases, générateur, rendus, contrôles, tests | ID10, ID28, DTS CNSS, DTS CNAMGS, DAS, ID18, ID27, ID23, ID24, ID26 : cases en données, générateur enregistré, imprimé V1 (ADR-20), classeur Excel / `.xlsm` officiel, contrôles, tests dédiés |
| Nombres en dur | noyau et règles : contrôle `check_odoo19_rules.py` ; générateurs : seules des positions de mise en page des classeurs (lignes, capacités) et le taux codé dans le classeur ID26 (formule du gabarit DGI, non écrit par le code) |
| Hypothèses du fichier 09 | paramètres datés ou options société documentées ; nouvelles : D-111 (convention Tronc commun, sources), D-113 (régime matrimonial ID19) |

## 2. Exécution (C4)

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | 490 tests, couverture 100 % |
| `make test MODULE=l10n_ga_hr_payroll` | 200 tests, 0 échec |
| `make test MODULE=l10n_ga_hr_payroll_account` | 32 tests, 0 échec |
| `make test MODULE=l10n_ga_dgi_edi` | 115 tests, 0 échec |
| `make test MODULE=l10n_ga_dgi_edi_account` | 34 tests, 0 échec |
| `make upgrade` × 4 | 200 / 32 / 115 / 34 tests, 0 échec, aucune erreur |
| 4 modules ensemble, base neuve (`--test-tags` des 4 modules) | **381 tests, 0 échec** |
| Installation puis désinstallation des 4 modules | propres : 4 modules désinstallés, 0 table `l10n_ga*` restante |
| Mise à jour réelle depuis la version démo (FIX 03, FIX 04) | OK (367 tests sur base mise à jour) ; démo `odoo19` mise à jour sans erreur |

## 3. Recette chiffrée (C5)

| Cas | Test | Écart |
|---|---|---|
| F16 590 000 → net 514 897 (noyau) | `lib/tests/test_engine_examples.py::test_case_590000_net_514897` | 0 |
| F16 dans Odoo, espèces arrondies à 500 | `test_payslip_ga.test_f16_net_514897_in_odoo`, `test_f16_paid_in_cash_rounded_to_500` | 0 |
| Parité avec `calcul_paie_gabon_reference.py` | `lib/tests/test_parity_reference.py` | ≤ 1 FCFA |
| Écriture comptable F16 | `l10n_ga_hr_payroll_account/tests/test_recette_f16.py` | 0 |
| ID10 = Σ bulletins payés du mois | `test_id10.test_f16_single_payslip`, `test_sum_of_paid_payslips_only` | 0 |
| DAS = Σ ID10 de l'année | `test_das.test_das_equals_sum_of_id10` | 0 |
| DTS = Σ cotisations du trimestre | `test_dts.test_full_quarter_cnss`, `test_full_quarter_cnamgs` | 0 |
| Imprimés et classeurs `.xlsm` = cases figées | `test_forms`, `test_official_workbooks` (×2) | 0 |

## 4. Bloquants et questions pour Alex

Aucun bloquant technique. Points de fond à confirmer (valeurs paramétrées, modifiables sans code) :
1. Taux CNSS 2026 5 % / 18 % (D-105) et FNH 3 % au 17/07/2026 (D-108) — fiabilité « probable / à vérifier ».
2. Taux des retenues non-résidents 20 % / 25 % (D-103) ; cellule du NIF de l'ID10 (D-74) ; format des
   portails CNSS / CNAMGS (D-83) ; mentions du bulletin (D-47).
3. Convention collective réelle du client (plafond d'ancienneté, grille complète, heures supplémentaires).
4. Essai du bouton « Générer le XML » des classeurs `.xlsm` dans Excel (LibreOffice absent du serveur :
   recalcul des formules non vérifiable ici ; recalcul forcé à l'ouverture).

## 5. Dette acceptée

- DAS imprimée en A4 paysage d'un seul tenant (ID19 compris) : wkhtmltopdf ne mélange pas les orientations.
- Validation des déclarations de la comptabilité réservée au groupe « Déclarant fiscal » (implique la paie).
- Paramètres de référence non lus (`l10n_ga_rmm_amount`, `l10n_ga_isr_resignation_ratio`).
