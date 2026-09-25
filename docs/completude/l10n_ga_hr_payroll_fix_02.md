# Complétude — FIX 02 : mise à jour bloquée, champ `l10n_ga_entry_exit_hours` « absent »

Date : 25/09/2026 — plan `docs/plans/fix_02_champ_absent.md` ; « go avec tes recommandations ».

## Cause (une phrase)

Le bouton « Mettre à jour » a été exécuté par un service Odoo démarré à 15:32, avant l'ajout du champ en Python à 15:44 (FIX 01) : le service lisait la nouvelle vue sur le disque mais gardait l'ancien Python en mémoire (cause A ; causes B et C écartées, preuves dans le plan).

## Score

**6 / 6 éléments attendus (100 %).**

| # | Élément (prompt FIX 02) | État | Preuve |
|---|---|---|---|
| 1 | Diagnostic prouvé (A confirmée, B et C écartées) | présent | plan §1 (`journalctl`, `stat`, `grep`, `ast.parse`) |
| 2 | Explication pour Alex | présent | `docs/incidents/2026-09-25_champ_absent_res_company.md` |
| 3 | Correction (aucun code, champ gardé dans la vue) + mise à jour propre de la base | présent | `make demo MODULE=l10n_ga_hr_payroll` : processus neuf puis redémarrage ; base `odoo19` : module 19.0.1.6.4 installé, champ dans `ir_model_fields`, vue `res_company_view_form_l10n_ga_payroll` contenant le champ, 3 sociétés à « deduct », aucune erreur dans le journal depuis |
| 4 | Garde-fou Makefile | présent | `demo` documenté (processus neuf puis redémarrage), alias `update-demo` ; `upgrade` = processus neuf sur base de test (inchangé) |
| 5 | Règle `CLAUDE.md` §5 (et §7 C3) | présent | redémarrer après toute modification `.py`, jamais le bouton de l'interface |
| 6 | Contrôle automatique des champs des vues | présent | `tools/check_view_fields.py` (hook pre-commit `view-fields`, donc `make lint`) + 6 tests `tools/tests/test_check_view_fields.py` : champ mal orthographié, sur un autre modèle, champ créé par une fonction (`_frozen_amount`), sous-vue d'un `xpath`, dépôt entier cohérent |

## Pourquoi les tests n'ont pas attrapé l'incident

`make test` démarre un **processus neuf** sur une **base neuve** : il charge le Python du disque, donc connaît le champ ; la vue s'installe et les 188 tests passent. L'incident ne venait ni du code ni de la vue, mais d'un processus ancien : aucun test de code ne peut le reproduire, d'où la règle d'exploitation (redémarrage) et la procédure `make demo`.

## Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur (nouveau contrôle `view-fields` compris) |
| `make test-core` | 79 tests d'outillage + 490 tests du noyau, couverture 100 % |
| `make test MODULE=l10n_ga_hr_payroll` | 188 tests, 0 échec |
| `make demo MODULE=l10n_ga_hr_payroll` | mise à jour réussie sur `odoo19`, service redémarré |

## Dette acceptée

Le contrôle statique ne vérifie que les champs `l10n_ga_*` (les champs d'Odoo ne sont pas dans le dépôt) ; dans une sous-vue atteinte par `xpath`, il vérifie seulement que le champ existe sur un modèle du dépôt (modèle lié inconnu hors d'Odoo).
