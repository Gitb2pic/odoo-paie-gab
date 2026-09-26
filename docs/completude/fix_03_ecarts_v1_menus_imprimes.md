# Complétude — FIX 03 : écarts V1, menus Comptabilité, vue et imprimés au format V1

26/09/2026. Plan : `docs/plans/fix_03_ecarts_v1_menus_imprimes.md`. Analyse : `docs/analyses/ecarts_v1_hr_payroll_gb.md`.
ADR : `docs/adr/ADR-20-imprimes-format-v1.md`. Décisions D-105 à D-110 (« go avec tes recommandations »).

**Score : 16 / 16 éléments présents et testés (100 %).**

## C1 — Inventaire

| # | Élément | Fichier | État |
|---|---|---|---|
| A1 | Convention par défaut de la société | `l10n_ga_hr_payroll/models/res_company.py`, vue société | présent, testé |
| A2 | Convention effective (version, sinon société) pour ancienneté, heures sup., anomalies | `hr_version.py` `_l10n_ga_agreement`, `hr_payslip.py` | présent, testé |
| A3 | Paramètre daté `l10n_ga_seniority_check_years` (YAML → XML généré) | YAML, `param_codes.py`, `hr_rule_parameters_data.xml` | présent, `--check` OK |
| A4 | Contrôle bloquant `GA_NO_AGREEMENT` | `l10n_ga_payroll_check.py` | présent, testé |
| A5 | Contrôle bloquant `GA_OVERTIME_NO_RATE` | idem | présent, testé |
| B1 | Champ `scope` (type, stocké sur la déclaration) ; ID18, ID27, ID23, ID24, ID26 = `account` | moteur + données compta | présent, testé (fraîche et mise à jour) |
| B2 | Menus paie filtrés `scope = payroll` + ID10 / ID28 / DTS / DAS | `l10n_ga_dgi_edi/views/menus.xml`, `..._id10_views.xml` | présent, testé |
| B3 | Comptabilité → Analyse → Déclarations DGI (Échéances, Toutes, ID18, ID27, Annexes, Quittances) | `l10n_ga_dgi_edi_account/views/menus.xml` | présent, testé |
| B4 | Accès comptables limité aux imprimés de la comptabilité (ACL + règles de groupe) | `l10n_ga_dgi_edi_account/security/*` | présent, testé |
| C1 | Vue formulaire / liste ID10 au format V1 (cadres 1 à 4) | `l10n_ga_declaration_id10_views.xml` | présent, testé |
| C2 | Champs d'affichage `id10_*`, total en lettres (français) | `l10n_ga_declaration_form.py` | présent, testé |
| C3 | Imprimé ID10 au format V1 = `report_id` du type (PDF figé à la validation) | `report/report_forms.xml` | présent, testé |
| D1 | Imprimés V1 : ID28, DTS, DAS (ID20, ID22, ID21, ID19 par salarié), générique | `report/report_forms.xml` | présent, testé |
| D2 | Imprimés V1 : ID18 / ID27, ID23 / ID24 / ID26 | `l10n_ga_dgi_edi_account/report/report_forms.xml` | présent, testé |
| D3 | Classeur conservé en PDF secondaire (bouton « Classeur (PDF) ») | `action_print_workbook` | présent, testé |
| D4 | Calcul d'une déclaration de la compta par un comptable sans accès paie | `_write_details` | corrigé, testé |

## C2 — Traçabilité

| Exigence | Code | Test |
|---|---|---|
| D-106 (règle d'or 13 : jamais silencieux) | `MissingAgreementForSeniority`, `_l10n_ga_agreement` | `test_checks.test_no_agreement_blocks_senior_employee`, `test_company_default_agreement_is_effective`, `test_agreement.test_seniority_from_company_default_agreement` |
| D-107 | `OvertimeWithoutRate` | `test_checks.test_overtime_without_rate` |
| Règle d'or 1 (seuil non codé en dur) | paramètre daté | `yaml_to_rule_parameters --check`, noyau 490 tests |
| Règle d'or 8 (valeur figée) | vue et imprimés lus sur `line_ids` | `test_forms.test_id10_display_fields_follow_frozen_value`, `test_id10_snapshot_is_v1_form` |
| Règle d'or 11 (multi-société) | règles globales inchangées + règles de groupe | `test_security`, `test_menus_forms.test_accountant_sees_only_accounting_declarations` |
| ADR-20 | `report_forms.xml`, `report_id` des types | `test_forms.*_form_report`, `test_das.test_workbook_and_pdf`, `test_das_fees.test_annual_workbook`, `test_menus_forms.test_*_form` |
| Demande « compta : seulement eux » | `scope`, menus, règles | `test_menus_forms.test_menu_under_accounting_reporting`, `test_types_scope` |

## C3 — Chasse aux trous

Aucun `TODO/FIXME/XXX/HACK` dans les fichiers ajoutés ; manifestes à jour (tous les fichiers déclarés
existent) ; ACL pour les comptables sur tous les modèles lus par le formulaire ; `view-fields` OK ;
aucune syntaxe pré-19 ; libellés en français.

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | 490 tests, couverture 100 % |
| `make test MODULE=l10n_ga_hr_payroll` | 192 tests, 0 échec |
| `make test MODULE=l10n_ga_dgi_edi` | 107 tests, 0 échec |
| `make test MODULE=l10n_ga_dgi_edi_account` | 29 tests, 0 échec |
| 4 modules installés ensemble, base neuve | **360 tests, 0 échec** |
| `make upgrade MODULE=l10n_ga_dgi_edi` | 107 tests, 0 échec |
| Mise à jour réelle depuis `0e089c6` (version de la démo) avec déclarations existantes | mise à jour sans erreur ; `scope` rempli (ID10 = paie, ID18 = compta) ; `report_id` basculés ; 360 tests dont 1 erreur due au jeu de données ajouté (aide de test sans filtre société, corrigée) |

## C5 — Recette

Montants inchangés : l'ID10 F16 imprimée affiche IRPP 23 195, TCS 13 058, CFP 2 775 (écart 0 avec les cases).

## Bloquants / à faire par Alex

1. **Démo `odoo19`** : 85 salariés ont ≥ 2 ans sans convention → la prochaine paie sera bloquée par
   `GA_NO_AGREEMENT` tant que la **convention par défaut** de la société n'est pas renseignée
   (Paramètres → Société → Gabon — Paie et fiscalité), p. ex. « EXEMPLE — Tronc commun » (2 % à 2 ans, +1 %/an)
   ou la vraie convention du client.
2. Mise à jour de la démo : `make update-demo MODULE=l10n_ga_hr_payroll` (redémarre le service), non lancée
   sans accord.

## Dette acceptée

- La DAS est imprimée en A4 paysage d'un seul tenant (ID19 compris) : wkhtmltopdf ne mélange pas les
  orientations ; l'ID19 V1 était en portrait.
- Un comptable consulte et recalcule les imprimés de la comptabilité ; la validation reste réservée au
  groupe « Déclarant fiscal » (qui implique la paie), comme avant.
