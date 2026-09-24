# Plan — Sprint 0 : socle du dépôt et vérifications Enterprise

Date : 24/09/2026 — statut : **en attente du « go » d'Alex**

## 0. Reconnaissance déjà faite (lecture seule, rien modifié)

| Élément | Constat |
|---|---|
| Service | systemd `odoo19.service` (actif), `User=ubuntu`, `Restart=on-failure` |
| Commande | `/home/ubuntu/odoo/venv-odoo-19.0/bin/python3 /home/ubuntu/odoo/odoo/odoo-bin -c /home/ubuntu/odoo/odoo/debian/odoo.conf` |
| Version | Odoo 19.0 FINAL — Community `2e2acfd6` (24/09/2026), Enterprise `35b39159` (24/09/2026) |
| Python | 3.14.4 (venv Odoo et système) |
| `$ODOO_PATH` | `/home/ubuntu/odoo/odoo` (addons : `/home/ubuntu/odoo/odoo/addons`) |
| `$ENTERPRISE_PATH` | `/home/ubuntu/odoo/enterprise` (contient `hr_payroll`, `hr_payroll_account`, `hr_payroll_holidays`, `l10n_account_withholding_tax`) |
| `addons_path` | enterprise, community, **`/home/ubuntu/odoo/extra-addon`** ✔ |
| Contenu de `extra-addon` | uniquement `CLAUDE.md`, `docs/`, `prompts/`, `.claude/` — **aucun module tiers** à exclure |
| PostgreSQL | rôle `ubuntu` avec `CREATEDB` ✔ ; bases existantes : `odoo19`, `postgres` (jamais touchées) |
| Port HTTP | production sur 8069 → les tests utiliseront un port libre calculé (≥ 8169) |
| Ressources | 3,7 Go RAM (≈ 2 Go dispo), 26 Go disque libres — tests Odoo à lancer un par un |

## 1. Livrables

| # | Fichier / élément | Contenu |
|---|---|---|
| 1 | `.gitignore` | Python, `.venv/`, caches, `filestore/`, `.env`, `*.log`, `docs/sources_pdf/` (lourd, à confirmer), `.claude/settings.local.json` |
| 2 | `git init -b main` | premier commit `chore: socle du dépôt` |
| 3 | `docs/environnement_vps.md` | tableau ci-dessus + commandes (restart, logs `journalctl -u odoo19`, createdb/dropdb) — aucun mot de passe |
| 4 | `docs/PROGRESS.md` | tableau des étapes (Sprint 0, 2.1→2.7, 3, 4.1→4.5, 5, 6 + complétudes), toutes « à faire », section ADR proposés |
| 5 | `.venv` (Python 3.14) | `ruff`, `pytest`, `pytest-cov`, `pre-commit`, `pylint-odoo`, `pyyaml` (pour les tests noyau) |
| 6 | `pyproject.toml` | ruff `target-version = "py314"` (repli `py313` si non supporté), règles Odoo-friendly ; pytest `testpaths = ["l10n_ga_hr_payroll/lib"]`, `--cov=l10n_ga_hr_payroll/lib/ga_fiscal_core --cov-fail-under=90` |
| 7 | `.pre-commit-config.yaml` | ruff, ruff-format, pylint-odoo (`--valid-odoo-versions=19.0`), lint XML (`check-xml`) + hooks de base |
| 8 | `Makefile` | `lint`, `test-core`, `test MODULE=`, `upgrade MODULE=`, `shell`, `restart`, `logs` (voir §2) |
| 9 | `docs/sprint0_verifications_enterprise.md` | 14 points : réponse, preuve `chemin:ligne`, extrait, impact |
| 10 | `docs/adr/ADR-18-check-issue-dans-la-paie.md` | proposé (voir §4) + autres ADR si un point contredit l'architecture |
| 11 | `docs/decisions/ouvertes.md` | conflits documentaires relevés (§3) |
| 12 | `docs/completude/sprint0.md` | protocole C1-C7 |

## 2. Makefile — comportement prévu

- `ODOO_BIN`, `ODOO_CONF`, `ODOO_PY` = chemins réels du service (surchargeables).
- `test MODULE=x` : base `test_ga_x_<AAAAMMJJHHMMSS>`, `odoo-bin -c odoo.conf -d <base> -i x --test-tags /x --stop-after-init --without-demo=all --http-port=<port libre> --log-level=test`, puis `dropdb` de la base **et** de son filestore, même en cas d'échec (code de sortie conservé). Garde-fou : refuse toute base qui ne commence pas par `test_ga_`.
- `upgrade MODULE=x [DB=test_ga_…]` : installe sur base neuve puis relance avec `-u x` (test de mise à jour), mêmes garde-fous.
- `restart` : `sudo systemctl restart odoo19` (commande explicite, jamais appelée par `test`).
- `test-core` : `pytest` ; dépôt vide → code 5 « no tests collected » traité comme succès tant que `lib/` n'existe pas.
- Le service de production n'est jamais arrêté : tests sur un autre port, `--stop-after-init`.

## 3. Écarts documentaires déjà repérés (à consigner, non tranchés seul)

1. **« 10 points » du prompt vs 8 points** dans `05_integration_odoo.md` §7 (et « 8 points » dans `06` §6). Proposition : traiter les 8 points + **9.** `hr.salary.attachment` (accepte-t-il des gains ? → ADR-16) + **10.** vue formulaire de `hr.salary.rule` et groupes `hr_payroll` (🔒 de `05` §2.3 et `01`), puis 11-14 du prompt = 14 points.
2. **ADR-16 et ADR-17** cités par `CLAUDE.md` (§3 règles 6-7) mais **absents** de `00_INDEX` (qui s'arrête à ADR-15) et de tout le dossier `docs/`. → entrée dans `ouvertes.md` ; je ne les rédige pas sans ta validation (sauf si le point 9 impose ADR-16, auquel cas brouillon « proposé »).
3. **Point 8** (schéma des tables `hr_payroll_gb` chez le client) : non vérifiable ici (pas de base client ni de module sur le VPS) → « non vérifiable » + question.
4. Arborescence `06` §1 nommée `odoo-ga-payroll/` alors que le dépôt est `extra-addon/` : sans impact (modules à la racine), noté dans `environnement_vps.md`.

## 4. ADR-18 (proposé)

`l10n_ga.check.issue` défini dans `l10n_ga_hr_payroll` (champs `company_id`, `payslip_run_id`, `payslip_id`, `employee_id`, `code`, `severity`, `message`, `scope` = « lot »), étendu dans `l10n_ga_dgi_edi` par `_inherit` (`declaration_id`, sélection `scope` += « déclaration »). Respecte la règle de dépendance `01` §3. Conséquence : mise à jour de `06` §1 (déplacement du fichier) après validation.

## 5. Tests / vérifications

- `make lint` sur dépôt sans code → 0 erreur.
- `make test-core` → vert (aucun test collecté, accepté explicitement).
- Contrôle à blanc de `make test` / `make upgrade` avec un module Community léger (**`base_setup`**) : valide création de base `test_ga_*`, port libre, suppression base + filestore. Un essai `hr_payroll` complet serait trop lourd pour ce sprint (RAM).

## 6. Risques

| Risque | Parade |
|---|---|
| `pylint-odoo` / ruff incompatibles Python 3.14 | fixer les versions qui fonctionnent, sinon repli `target-version py313` documenté |
| RAM limitée (2 Go dispo) pendant les tests | un seul test Odoo à la fois, `--workers` absent (mode threadé) |
| Écriture accidentelle sur `odoo19` | garde-fou `test_ga_*` dans le Makefile, `dropdb` limité à ce préfixe |
| `sudo` requis pour `restart` | cible documentée, jamais invoquée automatiquement |

## 7. Commits prévus

1. `chore: initialise le dépôt (gitignore, docs de suivi)`
2. `build: outillage lint/tests (pyproject, pre-commit, Makefile)`
3. `docs: vérifications Enterprise du sprint 0`
4. `docs(adr): ADR-18 check.issue dans la paie (proposé)`
5. `chore: complétude sprint 0`
