# Complétude C-2 — module `l10n_ga_hr_payroll_account` (25/09/2026)

Périmètre : module complet (étape 3). Vérification transversale selon `prompts/99_completude.md`, en repartant du rapport `l10n_ga_hr_payroll_account.md`.

## Score

**18 / 18 éléments attendus présents et testés (100 %)**, après correction de **2 manques** trouvés par cette passe (ci-dessous). 32 tests du module ; 210 tests des deux modules installés ensemble.

## Manques trouvés et complétés

| # | Manque | Gravité | Correction | Test |
|---|---|---|---|---|
| M1 | Société au plan `ga_syscebnl` (associations) : la structure Gabon n'a pas de journal, le contrôle `GA_NO_ACCOUNT` ne s'appliquait pas et les bulletins étaient validés **sans écriture, en silence** — contraire à D-62 (« signalé ») | haute | le contrôle s'applique dès que la société a un plan comptable ; il bloque aussi une structure sans journal de paie | `TestSyscebnlCompany.test_syscebnl_company_is_blocked`, `test_missing_journal_blocks`, `test_company_without_accounting_is_not_checked` |
| M2 | Installation groupée paie + comptabilité : le test de la paie `test_abstract_rule_and_custom_chain` supposait la chaîne F8 exacte ; le module comptable l'étend → 1 échec sur 210 | moyenne (test) | le test vérifie que la chaîne de la paie est un **préfixe** | exécution groupée |
| M3 | Fonctions sans test nommé (`_configure_payroll_account_ga`, `missing_account_rules`) | faible | tests directs | `test_configure_payroll_account_ga_entry_point`, `test_missing_account_rules_lists_codes` |

## C1 — Inventaire

Inchangé par rapport à `docs/completude/l10n_ga_hr_payroll_account.md` (18 éléments), avec l'élément 17 étendu : `GA_NO_ACCOUNT` couvre aussi le journal manquant.

## C3 — Chasse aux trous (module)

| Contrôle | Résultat |
|---|---|
| TODO / stubs | 0 |
| Manifeste ↔ fichiers | 3/3 |
| Droits / record rules | aucun nouveau modèle |
| Nombres en dur | 0 |
| Syntaxe pré-19 | 0 |
| Chaque rubrique du catalogue : compte ou « sans écriture » justifié | 72 + 4, test `test_table_matches_catalogue` |
| Points 🔒 | point 4 du sprint 0 (confirmé), ADR-19 d |
| Hypothèses du fichier 09 | aucune touchée (choix comptables = D-58 à D-64) |
| Messages traduisibles | `env._`, `i18n` régénéré (2 messages du contrôle) |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | 483 tests, couverture 100 % (noyau inchangé) |
| `make test MODULE=l10n_ga_hr_payroll_account` | 32 tests, 0 échec, 0 ERROR ; 5 WARNING d'environnement |
| `make upgrade MODULE=l10n_ga_hr_payroll_account` | 32 tests, 0 échec, 0 ERROR ; 10 WARNING d'environnement |
| Paie + comptabilité installées ensemble, `--test-tags /l10n_ga_hr_payroll,/l10n_ga_hr_payroll_account` | 210 tests (178 + 32), 0 échec, 0 ERROR (avant correction M2 : 1 échec) |
| Installation sur société existante / désinstallation | propres (rapport de l'étape 3) |

## C5 — Recette chiffrée

F16 en comptabilité (`test_recette_f16.py`) : écart 0 sur chaque compte.

## Bloquants et questions pour Alex

Aucun. D-47 (mentions du bulletin) reste ouvert, hors de ce module.

## Dette technique acceptée

Identique à l'étape 3 (D-61, D-62, D-64 ; `employee_move_line` laissé coché après désinstallation). Plan `ga_syscebnl` : la paie est désormais **bloquée** jusqu'à une table dédiée.
