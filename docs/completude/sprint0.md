# Complétude — Sprint 0 (socle du dépôt et vérifications Enterprise)

Date : 24/09/2026. Protocole `CLAUDE.md` §7 appliqué au périmètre du sprint 0 (aucun code métier).

## Score

**33 / 33 éléments attendus présents et vérifiés = 100 %** (16 éléments de socle et d'outillage + 14 points Enterprise + 3 éléments ADR). Bloquants : aucun pour l'étape 2.1. Questions ouvertes pour des étapes ultérieures : D-04 à D-08 (voir plus bas).

## C1 — Inventaire attendu / réel

| # | Élément attendu (prompt 01) | État | Chemin / preuve |
|---|---|---|---|
| 1 | Reconnaissance : service, conf, utilisateur, `odoo-bin`, version, Python, `addons_path`, chemins Enterprise/Community | présent | `docs/environnement_vps.md` |
| 2 | `extra-addon` dans l'`addons_path`, modules tiers signalés | présent (aucun module tiers ; dossier ignoré par Odoo tant qu'il est vide, documenté) | `docs/environnement_vps.md` §Dépôt |
| 3 | Accès PostgreSQL pour bases `test_ga_*`, bases existantes intactes | présent (`CREATEDB` ✔, `odoo19`/`postgres` jamais touchées) | `docs/environnement_vps.md` |
| 4 | Aucun mot de passe dans le dépôt | vérifié (`git grep` : seul un exemple fictif dans une skill `.claude`) | C3 |
| 5 | `git init`, branche `main` | présent | `git log` (5 commits) |
| 6 | `.gitignore` (Python, pyc, filestore, `.env`, `sources_pdf`) | présent | `.gitignore` |
| 7 | `docs/plans/` | présent | `docs/plans/sprint0.md` |
| 8 | `docs/completude/` | présent | ce fichier |
| 9 | `docs/adr/` | présent | ADR-16 à ADR-19 |
| 10 | `docs/decisions/ouvertes.md` | présent | D-01 à D-08 |
| 11 | `docs/PROGRESS.md` (étapes de `00_LISEZMOI`, « à faire ») | présent | 21 lignes d'étapes + ADR proposés |
| 12 | `.venv` avec ruff, pytest, pytest-cov, pre-commit, pylint-odoo | présent | ruff 0.16.8, pytest 9.1.1, pytest-cov 7.1.0, pre-commit, pylint 4.0.9 / pylint-odoo 10.0.11, PyYAML 6.0.3 |
| 13 | `pyproject.toml` : ruff (Python d'Odoo), pytest (`testpaths`, `--cov` noyau, seuil 90 %) | présent | `pyproject.toml` (`py314`, `--cov-fail-under=90`) |
| 14 | `.pre-commit-config.yaml` : ruff, ruff-format, pylint-odoo 19, lint XML | présent (+ hook `odoo19-rules`) | `.pre-commit-config.yaml`, `.pylintrc` |
| 15 | `Makefile` : `lint`, `test-core`, `test`, `upgrade`, `shell`, `restart` | présent (+ `logs`, `help`) | `Makefile`, `tools/odoo_test.sh` |
| 16 | `make test` : base neuve `test_ga_<module>_<horodatage>`, port libre, supprimée ensuite | présent, testé | C4 |
| 17-30 | Points Enterprise 1 à 14, chacun avec réponse, preuve `chemin:ligne`, extrait, impact | 14/14 (point 8 : « non vérifiable » + raison + question) | `docs/sprint0_verifications_enterprise.md` |
| — | ADR pour chaque contradiction avec l'architecture | présent | ADR-16 (point 9), ADR-19 (points 3, 4, 12, 13) |
| — | ADR-18 check.issue (proposé) | présent | `docs/adr/ADR-18-check-issue-dans-la-paie.md` |
| — | ADR proposés listés dans `PROGRESS.md` | présent | `docs/PROGRESS.md` §ADR |

## C2 — Traçabilité (périmètre sprint 0)

| Exigence | Réalisation | Vérification |
|---|---|---|
| Règle d'or 2 (noyau sans `odoo`) | hook `odoo19-rules` (analyse AST) | `tools/tests/test_check_odoo19_rules.py::test_odoo_import_forbidden_in_core`, `::test_odoo_import_allowed_outside_core` |
| Conventions 19 (`models.Constraint`, `<list>`, pas d'`attrs`) | hook `odoo19-rules` | `test_sql_constraints_detected`, `test_attrs_and_tree_detected`, `test_list_view_and_constraint_accepted` |
| Qualité (`ruff`, `pylint-odoo`) | `make lint` | essai sur un module factice (scratchpad) : `resource-not-exist`, `unused-import`, `attribute-string-redundant` détectés |
| Couverture ≥ 90 % du noyau | `pyproject.toml` | appliquée dès que `l10n_ga_hr_payroll/lib` existe (étape 2.1) |
| CLAUDE.md §5 (bases `test_ga_`, service jamais arrêté) | `tools/odoo_test.sh`, `make shell` | refus de `MODULE='x;rm'`, refus `make shell DB=odoo19`, port libre ≠ 8069, aucune base résiduelle |
| CLAUDE.md §2 (preuves `chemin:ligne`) | rapport des 14 points | numéros de ligne revérifiés par `grep -n` |
| Règle d'or 14 / `01` §3 (dépendances) | ADR-18 | — (documentaire) |

## C3 — Chasse aux trous

| Contrôle | Résultat |
|---|---|
| fichiers vides (hors `__init__.py`) | 0 |
| `TODO`, `FIXME`, `XXX`, `HACK`, « à compléter », `NotImplementedError` hors documents d'entrée | 0 |
| secrets | 0 (le seul motif trouvé est un exemple dans `.claude/skills/ecc-security-review`) |
| manifeste / modèles / vues / nombres en dur | sans objet (aucun module) |
| méthodes publiques sans test | `tools/check_odoo19_rules.py` : `check_file`, `main` testés (6 tests) |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur (`check-yaml`, `check-toml`, ruff, ruff-format passent ; hooks Odoo sans fichier à analyser) |
| `make test-core` | 6 tests d'outillage passent ; noyau absent (créé à l'étape 2.1) → couverture non mesurable à ce stade, annoncée |
| `make test MODULE=base_setup` (essai à blanc) | vert : 11 tests, 0 échec, 0 ligne ERROR, base et filestore supprimés |
| `make upgrade MODULE=base_setup` (essai à blanc) | vert : installation puis `-u`, 7 tests `post_install`, 0 échec, 0 ligne ERROR, 10 WARNING de configuration (listés dans `environnement_vps.md`), base supprimée |
| `make test MODULE='x;rm'` | refusé (« nom de module invalide »), code 2 |
| `tools/odoo_test.sh test l10n_ga_nexiste_pas` | échec attendu (« module introuvable »), code 1, base supprimée |
| `make shell DB=odoo19` | refusé (« DB doit commencer par test_ga_ ») |

Problèmes trouvés et corrigés pendant C4 :
1. la base du premier essai n'était pas supprimée : connexions cron du service de production (PID 18556) → `dropdb --force` + D-04 ;
2. la phase `-u` lançait les tests `at_install` de `base_setup` sur un registre partiel (erreur `color_scheme` NOT NULL de `web_enterprise`) → phase `-u` limitée aux tests `post_install` (convention du projet) ;
3. module inexistant accepté avec 0 test → échec explicite ;
4. injection possible via `MODULE` dans le Makefile → variables entre guillemets + validation du nom.

## C5 — Recette fonctionnelle

Sans objet au sprint 0 (aucun calcul de paie). Les cas chiffrés (fichier 04 §8, F16 590 000 → 514 897) démarrent à l'étape 2.1.

## Bloquants et questions pour Alex

Aucun bloquant pour l'étape 2.1. À trancher (`docs/decisions/ouvertes.md`) :
- **D-04** : ajouter `db_name = odoo19` à la configuration de production et redémarrer (je ne touche pas à la production sans ton accord) ;
- **D-05** : dump anonymisé (ou schéma) des tables `hr_payroll_gb` avant l'étape 6 ;
- **D-06** : date de référence des paramètres (`date_to` ou date de paiement), à l'étape 2.2 ;
- **D-07** : code de la V1 `l10n_ga_dgi_edi` avant l'étape 4 ;
- **D-08** : validation d'ADR-16, 17, 18, 19 (puis j'amende `02`, `04`, `05`, `06`).

## Dette technique acceptée

- Contrôle de couverture du noyau non exercé tant que le noyau n'existe pas (étape 2.1).
- `make upgrade` ne rejoue pas les tests `at_install` après `-u` (justification ci-dessus ; les tests du projet sont `post_install`).
- Essais à blanc faits sur `base_setup`, pas sur `hr_payroll` (RAM limitée) ; le premier vrai passage `hr_payroll` aura lieu à l'étape 2.2.
- L'identité git globale du VPS (`user.name`/`user.email`) n'est pas celle d'Alex ; laissée telle quelle (configuration système), à corriger si besoin.
