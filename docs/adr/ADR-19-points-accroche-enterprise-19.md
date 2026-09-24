# ADR-19 — Points d'accroche Enterprise 19 corrigés après le sprint 0

- **Statut** : proposé (sprint 0, 24/09/2026) — à valider par Alex
- **Origine** : `docs/sprint0_verifications_enterprise.md`, points 3, 4, 12 et 13, qui contredisent des hypothèses 🔒 de l'architecture. Cet ADR regroupe les ajustements pour ne pas modifier l'architecture en silence (CLAUDE.md §8).

## Décisions

| # | Hypothèse de l'architecture | Constat Enterprise 19 | Décision |
|---|---|---|---|
| a | États `done`, `paid` (`04` §3 : `('slip_id.state', 'in', ('done', 'paid'))`) | États `draft/validated/paid/cancel` (`hr_payslip.py:67-72`) | Filtrer sur `('validated', 'paid')` partout ; interdit de tester `'done'`. |
| b | Observer sur `hr.payslip.run.action_validate()` (`04` §11, ADR-10) | Le lot délègue à `hr.payslip.action_payslip_done()`, aussi appelé par la validation d'un bulletin seul (`hr_payslip_run.py:291-294`, `hr_payslip.py:643-645`) | S'accrocher à **`hr.payslip.action_payslip_done()`** (et à `action_payslip_paid()` pour ce qui dépend du paiement). ADR-10 inchangé sur le principe. |
| c | Bulletin figé (F7/F16) « à la validation » | `action_payslip_done()` écrit `state='validated'` ; `hr_payroll_account` crée les pièces après `super()` | Stocker les valeurs figées **avant** `super().action_payslip_done()` (bulletin encore brouillon, lignes calculées), dans la même transaction. |
| d | Comptes des règles écrits par données XML (`05` §3) | `account_debit` / `account_credit` **`company_dependent`** (`hr_payroll_account/models/hr_salary_rule.py:11-16`) ; hook `_configure_payroll_account_<plan>` (`account_chart_template.py:21-69`) | `l10n_ga_hr_payroll_account` implémente `_configure_payroll_account_ga` (et `_ga_syscebnl`) + reconfiguration pour les sociétés existantes ; pas d'écriture XML des comptes. |
| e | Règle courante disponible dans `amount_python_compute` (`l10n_ga_prorate`) | Absente du localdict (`hr_salary_rule.py:159-194`) | Surcharger `hr.salary.rule._compute_rule()` pour ajouter `localdict['l10n_ga_rule'] = self` avant `super()`. |
| f | — | Deux règles de même code : écrasement silencieux de la ligne, double comptage dans les catégories (`hr_payslip.py:1224-1244`) | Test obligatoire d'unicité des codes par structure (déjà prévu `test_rule_codes_unique.py`) + contrainte `models.Constraint` / `@api.constrains` sur `(struct_id, code)` pour les structures Gabon. |

## Conséquences

- Fichiers à amender après validation : `04` §3 et §11, `05` §2.2 (ligne `hr.payslip`), §3, `02` (séquences « validation du lot »).
- Aucun changement de découpage des modules ni de modèle de données.
