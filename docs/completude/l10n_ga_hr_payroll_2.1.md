# Complétude — `l10n_ga_hr_payroll`, étape 2.1 : noyau fiscal pur

Date : 24/09/2026. Plan : `docs/plans/2.1.md` (validé : « go »). Protocole `CLAUDE.md` §7.

## Score

**25 / 25 éléments attendus présents et testés = 100 %.** Aucun bloquant. `make test` / `make upgrade` sans objet à cette étape (module Odoo non encore installable : manifeste à l'étape 2.2).

## C1 — Inventaire attendu / réel

| # | Élément (prompt 2.1, plan 2.1) | État | Fichier |
|---|---|---|---|
| 1 | `params.py` : `FiscalParams` figé, tous taux/plafonds/barèmes, `irpp_min_withholding`, plafonds d'exonération, arrondi espèces | présent | `lib/ga_fiscal_core/params.py` |
| 2 | `load_from_yaml(path, date)` (dernière date ≤ date, RG06) | présent | idem |
| 3 | `parts.py` : situation, enfants, infirmes, demi-part spéciale, forçage 1 à 6,5 | présent | `parts.py` |
| 4 | `social.py` : assiette, SMIG, CNSS/CNAMGS sal. et pat. (PF, AT, AVID), plafonds | présent | `social.py` |
| 5 | `tax.py` : base TCS (option CNAMGS), TCS, abattement plafonné, barème, parts, seuil F14, régularisation | présent | `tax.py` |
| 6 | `benefits.py` : avantages en nature | présent | `benefits.py` |
| 7 | `exemptions.py` : `GainLine`, `exemptions()`, `SOCIAL_CAPS` / `TAX_CAPS`, prorata, groupe inconnu, logement espèces documenté | présent | `exemptions.py` |
| 8 | `rounding.py` (F2) : multiple inférieur, reliquat, solde de tout compte | présent | `rounding.py` |
| 9 | `cash_breakdown.py` (F2) : coupures en paramètre | présent | `cash_breakdown.py` |
| 10 | `engine.py` : `PayslipFacts` → `compute` → `PayResult` (champs 04 §1 + détail par ligne) | présent | `engine.py` |
| 11 | API publique du package | présent | `ga_fiscal_core/__init__.py` |
| 12 | Tests exemples 04 §8 | présent (au franc) | `tests/test_engine_examples.py` |
| 13 | Cas 590 000 → 514 897 + montants listés, variante 486 617 | présent | idem |
| 14 | Jeux 06 §3 : sous seuil TCS, marié 3 enfants plafond CNSS, cadre plafond abattement, entrée le 15, 13e mois > 4 M, taux 01/01/2026 et 17/07/2026 | présent | idem |
| 15 | Départ avec régularisation IRPP | présent | idem + `test_tax.py` |
| 16 | `test_rounding.py` : reliquat sur 12 mois, somme versée = somme des nets | présent | `tests/test_rounding.py` |
| 17 | `test_exemptions.py` : plafond partagé, prorata, `forced_taxable`, groupe inconnu | présent | `tests/test_exemptions.py` |
| 18 | Test de parité paramétré avec l'oracle, ≤ 1 FCFA | présent (192 cas) | `tests/test_parity_reference.py` |
| 19 | Test AST : aucun import `odoo` | présent (+ hook pre-commit) | `tests/test_no_odoo_import.py` |
| 20 | Tests unitaires params / parts / social / tax / benefits / billetage | présents | `tests/test_*.py` |
| 21 | `make test-core` vert, couverture ≥ 90 % | 334 tests, **100 %**, 0,95 s | C4 |
| 22 | Paramètres manquants au YAML (F14, billetage, arrondi par défaut, bornes des parts forcées) | ajoutés (D-12) | `docs/base_connaissance/parametres_fiscaux_gabon_2026.yaml` |
| 23 | Décisions D-10 à D-14 consignées | présent | `docs/decisions/ouvertes.md` |
| 24 | `pythonpath` pytest, chemin pylint | présent | `pyproject.toml`, `.pylintrc` |
| 25 | Plan d'étape | présent | `docs/plans/2.1.md` |

## C2 — Traçabilité exigence → code → test

| Exigence | Code | Tests |
|---|---|---|
| RG03 parts (calcul, forçage) | `parts.tax_parts` | `test_parts.py` (tableau 04 §1.3, parité oracle 108 combinaisons, infirmes, demi-part, forçage, erreurs, valeurs lues dans les paramètres) |
| RG06 valeur datée = dernière ≤ date | `params._dated`, `load_from_yaml` | `test_params.py::test_dated_values_rg06`, `test_tcs_exemption_history`, `test_no_value_before_first_date` |
| RG23 / F2 arrondi espèces + reliquat | `rounding.cash_round` | `test_rounding.py` (12 mois, solde, pas 0, total négatif) |
| F2 billetage | `cash_breakdown.cash_breakdown` | `test_cash_breakdown.py` |
| F14 seuil de retenue IRPP (0 par défaut) | `tax.irpp_monthly` | `test_tax.py::test_irpp_min_withholding_f14`, `test_params.py` (valeur 0) |
| F16 cas 590 000 (prompt) | `engine.compute` | `test_case_590000_net_514897`, `test_case_590000_all_taxable_net_486617` |
| ADR-03 / règle d'or 2 noyau pur | package entier | `test_no_odoo_import.py` (AST, bibliothèque standard seule) + hook `odoo19-rules` |
| ADR-04 / règle d'or 1 rien en dur | `FiscalParams` | `test_params.py::test_values_2026_after_lfr`, `test_parts_come_from_parameters`, `test_fnh_employee_share_and_cfp_gross_options` ; chasse C3 |
| ADR-17 / règle d'or 7 exonérations par ligne, plafonds par groupe | `exemptions.py` | `test_exemptions.py` (15 tests) |
| Règle d'or 9 arrondi au franc à la ligne | `rounding.round_fcfa`, appels ligne par ligne | `test_rounding.py::test_round_fcfa_half_up`, `test_prorata_rounding_keeps_group_total` |
| Règle d'or 13 points non tranchés = paramètre / option | `tcs_deduct_cnamgs` (09-3), `fnh_employee_share` (09-2), `cfp_base` (D-10), `bonus_annual_cap` (09-4), `irpp_min_withholding` (F14) | `test_tcs_base_deducts_employee_contributions`, `test_fnh_employee_share_and_cfp_gross_options`, `test_options_override` |
| 04 §7 algorithme mensuel | `engine.compute` | exemples §8 + parité |
| 04 §7 régularisation annuelle | `tax.irpp_regularisation` | `test_regularisation_*` (3), `test_departure_with_regularisation` |
| 03 §1 SMIG plancher d'assiette | `social.social_base` | `test_social_base_floor_is_smig_times_presence`, `test_hired_on_15th_smig_floor` |
| 04 §5 avantages en nature (D-11) | `benefits.py`, `engine._benefit_lines` | `test_benefits.py`, `test_benefits_in_kind_enter_bases_but_not_cash` |

RG hors périmètre 2.1 (modèles Odoo) : RG02, RG05, RG07, RG08, RG18-RG22, RG24-RG26 → étapes 2.2 à 2.6.

## C3 — Chasse aux trous

| Contrôle | Résultat |
|---|---|
| `TODO`, `FIXME`, `XXX`, `HACK`, `NotImplementedError`, `pass`, `...` | 0 |
| imports `odoo` dans `ga_fiscal_core` | 0 (AST + hook) |
| nombres littéraux ≠ 0, 1, 100 | **trouvé et corrigé** : barème des parts (1 ; 1,5 ; 2 ; 0,5 ; bornes 1 et 6,5) et arrondi espèces 500 étaient dans le code → passés dans le YAML / `FiscalParams` (commit `86e184b`). Restants justifiés : `2` / `4` (codes du nombre de trajets, les montants sont des paramètres), `0.5` (pas de saisie d'une demi-part), `6` (chiffres anti-bruit flottant), `12` (mois de l'année) |
| méthodes publiques sans test | 0 (`round_fcfa`, `cash_round`, `cash_breakdown`, `load_from_yaml`, `tax_parts`, `social_base`, `social_contributions`, `tcs_base`, `tcs_amount`, `tax_one_part`, `irpp_monthly`, `irpp_regularisation`, `benefits_base`, `benefit_amount`, `exemptions`, `compute`) |
| manifeste / vues / droits / syntaxe pré-19 / `_()` | sans objet (aucun fichier Odoo à cette étape) ; libellés d'erreur du noyau en français, sans `_()` (le noyau n'importe pas `odoo`) — l'adaptateur (2.3) traduira les erreurs remontées à l'utilisateur |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur (ruff, ruff-format, odoo19-rules, pylint-odoo, check-yaml/toml/xml) |
| `make test-core` | **334 passed en 0,95 s** ; couverture **100 %** (297 instructions, 72 branches) ; 6 tests d'outillage |
| `make test MODULE=l10n_ga_hr_payroll` | sans objet : pas de `__manifest__.py` avant l'étape 2.2 |
| `make upgrade MODULE=l10n_ga_hr_payroll` | sans objet (idem) |
| tests `skip` / `xfail` / commentés | aucun |

## C5 — Recette chiffrée (noyau vs oracle `calcul_paie_gabon_reference.py`)

| Cas | CNSS sal. | CNAMGS sal. | TCS | IRPP | Net | CNSS pat. | CNAMGS pat. | FNH | CFP | Coût employeur | Écart max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Ex.1 | 25 750 | 10 300 | 16 448 | 33 500 | 459 002 | 92 700 | 21 115 | 15 450 | 2 575 | 676 840 | 0 |
| Ex.2 | 42 500 | 17 000 | 32 025 | 17 928 | 740 547 | 153 000 | 34 850 | 25 500 | 4 250 | 1 067 600 | 0 |
| Ex.3 | 75 000 | 40 000 | 86 750 | 245 080 | 1 553 170 | 270 000 | 82 000 | 45 000 | 7 500 | 2 404 500 | 0 |
| Ex.4 | 75 000 | 50 000 | 236 250 | 845 104 | 3 793 646 | 270 000 | 102 500 | 45 000 | 7 500 | 5 425 000 | 0 |
| 590 000 | 27 750 | 11 100 | 13 058 | 23 195 | **514 897** | 99 900 | 22 755 | 16 650 | 2 775 | 732 080 | 0 |

Variante « tout imposable » : net **486 617** (écart 0). Grille de parité : 192 cas × 14 montants, **écart maximal 1 FCFA** (TCS 18 fois, net 20 fois, IRPP 6 fois), dû à l'arrondi bancaire (`round`) de l'oracle face au demi supérieur du noyau (identique à `float_round` d'Odoo). Les paramètres du cas 590 000, absents des documents (D-13), ont été retrouvés en rejouant l'oracle : célibataire, 0 enfant, exclusion sociale 35 000, exonération fiscale 140 000.

## Bloquants et questions pour Alex

Aucun bloquant. Points fiscaux restant des paramètres à valeur par défaut documentée (règle d'or 13), à confirmer avec la DGI / un fiscaliste avant production : D-10 (base CFP), D-11 (base des avantages en nature), D-14 (logement en espèces, 09-5), 09-3 (CNAMGS dans la base TCS), 09-4 (gratifications 4 M), 09-2 (FNH 100 % employeur). Rappel : D-04 (`odoo.conf`) n'est pas encore appliqué ; il le faudra avant les tests Odoo de l'étape 2.2.

## Dette technique acceptée

- Messages d'erreur du noyau non traduisibles (pas de `_()` sans `odoo`) : l'adaptateur de l'étape 2.3 les enveloppera.
- `load_from_yaml` dépend de PyYAML (tests uniquement) ; en production les paramètres viendront de `hr.rule.parameter` (étape 2.2).
- Régularisation annuelle CNSS sur plafond annuel (09-14) non implémentée (plafond mensuel, conforme à l'hypothèse par défaut).
