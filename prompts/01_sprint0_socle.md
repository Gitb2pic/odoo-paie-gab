# Prompt 01 — Sprint 0 : socle du dépôt et vérifications Enterprise

> Environnement : VPS Ubuntu `ubuntu@164.132.106.87`, **Odoo 19 Enterprise déjà installé**.
> Dépôt de travail : `/home/ubuntu/odoo/extra-addon` (les documents y sont déjà copiés dans `docs/` et `prompts/`).

---

Tu démarres le projet « Paie Gabon & déclarations DGI V2 » (Odoo 19 Enterprise) sur le VPS. Aucun code métier dans ce sprint : on prépare le terrain et on lève les inconnues du code Enterprise.

## Entrées (déjà en place)

- `CLAUDE.md` à la racine de `/home/ubuntu/odoo/extra-addon`
- `docs/architecture/` (00 à 08 + diagrammes), `docs/base_connaissance/` (00 à 09, `parametres_fiscaux_gabon_2026.yaml`, `calcul_paie_gabon_reference.py`), `docs/templates_dgi/` (classeurs `.xlsx`), `docs/sources_pdf/` (textes et documents sources)
- `prompts/` : les prompts d'étape
- V1 `l10n_ga_dgi_edi` (facultatif) : à me demander si absente

## Travail demandé

### 0. Reconnaissance de l'installation existante (ne rien casser)
- Trouve le service Odoo (systemd ou Docker : `systemctl list-units | grep -i odoo`, `docker ps`), le fichier de configuration (`odoo.conf`), l'utilisateur système, `odoo-bin`, la version exacte, le Python/virtualenv utilisé, l'`addons_path` et le chemin des addons **Enterprise** (`$ENTERPRISE_PATH`) et Community (`$ODOO_PATH`).
- Vérifie que `/home/ubuntu/odoo/extra-addon` est bien dans l'`addons_path`. Liste son contenu : s'il contient déjà d'autres modules que les nôtres, **ne les modifie pas et ne les versionne pas** (`.gitignore`), et signale-le.
- Vérifie l'accès PostgreSQL pour créer des bases de test (`createdb` avec l'utilisateur d'Odoo) **sans jamais toucher aux bases existantes** (préfixe obligatoire `test_ga_`).
- Consigne tout dans `docs/environnement_vps.md` (chemins, service, commandes de redémarrage, versions). Aucun mot de passe dans le dépôt.

### 1. Dépôt git dans `/home/ubuntu/odoo/extra-addon`
- `git init`, branche `main`, `.gitignore` (Python, `*.pyc`, filestore, `.env`, modules tiers présents, `docs/sources_pdf/` si trop lourd).
- Compléter : `docs/plans/`, `docs/completude/`, `docs/adr/`, `docs/decisions/ouvertes.md`, `docs/PROGRESS.md` (tableau des étapes du fichier `prompts/00_LISEZMOI.md`, toutes « à faire »).

### 2. Outillage (sur l'installation existante, pas de Docker)
- Virtualenv de dev `.venv` (ou celui d'Odoo si imposé) avec `ruff`, `pytest`, `pytest-cov`, `pre-commit`, `pylint-odoo`.
- `pyproject.toml` : configuration `ruff` (version Python d'Odoo), `pytest` (`testpaths`, `--cov` sur `l10n_ga_hr_payroll/lib/ga_fiscal_core`, seuil 90 %).
- `.pre-commit-config.yaml` : ruff, ruff-format, `pylint-odoo` (règles Odoo 19), lint XML.
- `Makefile` utilisant le vrai `odoo-bin` et le vrai `odoo.conf` : `lint`, `test-core`, `test MODULE=`, `upgrade MODULE=`, `shell`, `restart`. `test` crée une base neuve `test_ga_<module>_<horodatage>` (`-c <odoo.conf> -d ... -i <module> --test-tags /<module> --stop-after-init --without-demo=all --http-port=<port libre>`), puis la supprime. Ne jamais arrêter le service de production pour tester.
- Vérifier que `make lint` et `make test-core` tournent (dépôt vide = OK).

### 3. Lecture du code Enterprise (le plus important)
Ouvre `<ENTERPRISE_PATH>/hr_payroll`, `hr_payroll_account`, `hr_payroll_holidays` et réponds aux **10 points du fichier `05_integration_odoo.md` §7**, plus :
- 11. Signature et comportement de `hr.rule.parameter` / `_rule_parameter(code)` (types de valeurs acceptés : nombre, liste, JSON ?) et date utilisée.
- 12. Ordre de calcul des règles (`sequence`), accès à la règle courante dans `amount_python_compute` (pour `l10n_ga_prorate`).
- 13. Méthode appelée à la validation d'un bulletin (pour figer F7/F16) et à la validation d'un lot (Observer, ADR-10).
- 14. Existence de `l10n_account_withholding_tax` dans `<ODOO_PATH>` ou `<ENTERPRISE_PATH>` 19.0 et son modèle de données.

Pour chaque point : réponse, **preuve `chemin:ligne`**, extrait de code court, **impact sur l'architecture** (aucun / ajustement / ADR nécessaire). Résultat dans `docs/sprint0_verifications_enterprise.md`.

Si un point contredit l'architecture (ex. `hr.salary.attachment` accepte les gains → ADR-16 s'applique ; `version_id` absent du bulletin), rédige l'ADR correspondant dans `docs/adr/` au statut « proposé » et signale-le à Alex.

### 4. Incohérence connue à trancher dans ce sprint
Le fichier 06 §1 place `l10n_ga_check_issue.py` dans `l10n_ga_dgi_edi`, mais les contrôles avant paie (F8) sont utilisés par `hr.payslip.run` dans `l10n_ga_hr_payroll`, qui ne peut pas dépendre de `l10n_ga_dgi_edi` (règle de dépendance, fichier 01 §3). Proposition à valider : définir `l10n_ga.check.issue` dans `l10n_ga_hr_payroll` (périmètre « lot »), l'étendre dans `l10n_ga_dgi_edi` (`declaration_id`, périmètre « déclaration »). Rédige `docs/adr/ADR-18-check-issue-dans-la-paie.md` (proposé).

## Critères de sortie

- Dépôt initialisé, `make lint` et `make test-core` verts.
- `docs/sprint0_verifications_enterprise.md` : 14 points traités, chacun avec preuve ou « non vérifiable » + raison.
- ADR proposés listés dans `docs/PROGRESS.md`.

## Fin obligatoire : protocole de complétude

Applique `CLAUDE.md` §7 sur le périmètre du sprint 0 (C1 : arborescence `docs/`, outillage, 14 points ; C3 : fichiers vides ou « à compléter » ; C4 : commandes Makefile). Rapport : `docs/completude/sprint0.md`. Commit, puis attends mon « go » pour l'étape 2.1.
