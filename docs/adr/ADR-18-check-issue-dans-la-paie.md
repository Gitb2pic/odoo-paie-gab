# ADR-18 — `l10n_ga.check.issue` défini dans la paie, étendu par les déclarations

- **Statut** : **accepté** (Alex, 24/09/2026 : « la meilleure option pour toi ») — proposé au sprint 0
- **Origine** : incohérence relevée par le prompt 01 §4.

## Contexte

- `06` §1 place `l10n_ga_check_issue.py` dans `l10n_ga_dgi_edi`.
- Or les contrôles avant paie (F8, `08` F8 ; `04` §8 `PAYROLL_CHECKS`) sont déclenchés par `hr.payslip.run` dans `l10n_ga_hr_payroll`, qui **ne peut pas dépendre** de `l10n_ga_dgi_edi` (règle de dépendance, `01` §3 ; règle d'or 14).
- Sprint 0 (point 13) : Odoo 19 a un **mécanisme natif d'anomalies de bulletin** : `hr.payslip.issues` (Json), `error_count`, `warning_count`, alimentés par `_get_errors_by_slip()` / `_get_warnings_by_slip()` ; `error_count > 0` **bloque** `action_payslip_done()` et `action_payslip_paid()` ; le lot affiche `payslips_with_issues` et `action_review_issues` (`E/hr_payroll/models/hr_payslip.py:150-152, 607-611, 1346-1456`).

## Décision

1. **`l10n_ga.check.issue` est défini dans `l10n_ga_hr_payroll`** (`models/l10n_ga_check_issue.py`) : `company_id` (obligatoire, `check_company`), `scope` (Selection `[('payslip_run', 'Lot de paie')]`), `payslip_run_id`, `payslip_id`, `employee_id`, `severity` (`blocking` / `warning`), `code`, `message`, `res_model` / `res_id`. Règle multi-société `company_id in company_ids`, droits paie.
2. **`l10n_ga_dgi_edi` l'étend** par `_inherit` : `declaration_id` et `selection_add=[('declaration', 'Déclaration')]` sur `scope` (`ondelete` défini).
3. La chaîne `PAYROLL_CHECKS` (patron 8) vit dans `l10n_ga_hr_payroll` ; `COMMON_CHECKS` / contrôles de déclaration dans `l10n_ga_dgi_edi` (réutilisent les classes de contrôle salarié de la paie).
4. **Pont avec le mécanisme natif** : les anomalies **bloquantes** rattachées à un bulletin sont aussi renvoyées par une surcharge de `hr.payslip._get_errors_by_slip()` (et les avertissements par `_get_warnings_by_slip()`), en ajoutant les dépendances Gabon à `_issues_dependencies()`. Ainsi le blocage de validation est celui du standard (pas de second verrou maison), et `l10n_ga.check.issue` reste la **source unique** affichée sur le lot et réutilisée par l'écran « Contrôle DAS ».

## Conséquences

- `06` §1 à corriger après validation : `l10n_ga_check_issue.py` passe dans `l10n_ga_hr_payroll/models/` ; `l10n_ga_dgi_edi/models/l10n_ga_check_issue.py` devient une extension.
- Fichiers `02` (UML `CheckIssue`) et `03` (MCD) inchangés sur le fond (le modèle reste unique).
- Tests : `test_checks.py` dans la paie (périmètre lot, blocage de `action_payslip_done`), et dans `l10n_ga_dgi_edi` (périmètre déclaration).

## Alternatives écartées

- Laisser le modèle dans `l10n_ga_dgi_edi` : viole la règle de dépendance.
- Deux modèles séparés (lot / déclaration) : double écran, contraire à F8 (« modèle unique »).
- Uniquement le mécanisme natif `issues` : limité aux bulletins (pas au lot avant calcul, ni aux déclarations), non requêtable (Json).
