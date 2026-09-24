# Prompt 03 — Module `l10n_ga_hr_payroll_account`

---

Tu développes le module `l10n_ga_hr_payroll_account` (dépend de `l10n_ga_hr_payroll` et `hr_payroll_account` 🔒, `auto_install: True`). Prérequis : module `l10n_ga_hr_payroll` complet (rapport de complétude global sans manque). Relis `CLAUDE.md`, `docs/PROGRESS.md`, `docs/sprint0_verifications_enterprise.md` (point 4 : champs comptables des règles, regroupement des écritures par lot).

**Architecture** : `05` §2.4 (colonne « Compte ») et §3 ; `03` RG09, RG17 ; `01` §3.

## Livrables

- `__manifest__.py` (`auto_install`), sécurité si nécessaire.
- Imputation des règles : débit/crédit selon le tableau `05` §2.4 et le catalogue `catalogue_rubriques_ga.csv` (colonne compte) — `pcg_6611`, `pcg_6612`, `pcg_6631` à `pcg_6638`, `pcg_6641`, `pcg_6413`, `pcg_6415`, `pcg_422`, `pcg_4211`, `pcg_4311`, `pcg_4312`, `pcg_4313`, `pcg_4318`, `pcg_4471`, `pcg_4472`.
- Les comptes étant créés **par société** au chargement du plan `l10n_syscohada` : liaison par `env['account.chart.template'].with_company(société).ref('pcg_xxx')` (vérifie `account/models/chart_template.py`) dans un hook post-installation **et** au chargement du plan pour une nouvelle société ; pas de xml_id de compte en dur dans les données.
- Journal de paie par société ; `GA_ROUND*` sans écriture propre (le reliquat reste dans 422).
- Rapprochements : solde 447x ↔ ID10 payée, 431x ↔ DTS payée (méthodes utilitaires réutilisées plus tard par `l10n_ga_dgi_edi`).

## Tests (`tests/test_payroll_move.py`)

- Lot de 3 salariés (virement, chèque, espèces) validé → écriture équilibrée, chaque rubrique sur le bon compte, total 422 = somme des `NET`.
- Deux sociétés avec plan SYSCOHADA : chaque écriture utilise les comptes de sa société.
- Nouvelle société créée après installation : comptes liés automatiquement.
- Prêt retenu → crédit 4211.

## Fin obligatoire

Protocole de complétude `CLAUDE.md` §7 sur tout le module (C1 : chaque règle du catalogue a ses comptes ou une justification « sans écriture ») ; rapport `docs/completude/l10n_ga_hr_payroll_account.md` ; commit ; `docs/PROGRESS.md` ; attends mon « go ».
