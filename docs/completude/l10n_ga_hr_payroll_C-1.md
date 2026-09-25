# Complétude C-1 — module `l10n_ga_hr_payroll` (25/09/2026)

Périmètre : module complet (étapes 2.1 à 2.7 b). Aucune fonctionnalité nouvelle ; vérification transversale.

## Score

Éléments attendus du module (rapports 2.1 à 2.7, chacun à 100 %) : **tous présents et testés**. Aucun manque de code nouveau détecté ; aucun code ajouté dans cette étape.

## C1/C2 — Inventaire et traçabilité

Les inventaires détaillés par étape restent dans `docs/completude/l10n_ga_hr_payroll_2.1.md` à `2.7.md`. Contrôle transversal des règles de gestion du périmètre (fichier 03) :

| RG | Objet | Test / preuve |
|---|---|---|
| RG01, RG07, RG08 | société, bulletin, lignes | modèles standard Odoo, exercés par tous les tests de bulletin |
| RG02-RG04 | versions, parts, convention | `test_agreement.py`, `test_tax_parts.py`, `test_hr_version_ga.py` |
| RG05, RG06, RG22 | rubriques, paramètres datés, code unique | tests 2.2 |
| RG18 | grille : salaire ≥ minimum | tests 2.4 |
| RG19-RG21 | prêts, échéances | tests 2.5 |
| RG23 | espèces et arrondi | tests 2.6 (F16 : 514 500 + reliquat 397) |
| RG24 | bulletin figé | tests 2.3 / 2.7 |
| RG25, RG26 | cumuls d'ouverture, contrôles avant paie | tests 2.6 |
| RG09-RG17, RG27-RG30 | comptabilité, déclarations | hors périmètre (étapes 3, 4, 5) |

## C3 — Chasse aux trous

| Contrôle | Résultat |
|---|---|
| TODO / FIXME / stubs | 0 ; seule occurrence : `NotImplementedError` de l'interface abstraite du patron 8 (`models/l10n_ga_payroll_check.py:27`), testée |
| Manifeste ↔ fichiers | tous les fichiers cités existent ; `data/catalogue_rubriques_ga.csv` non déclaré **volontairement** (source du générateur `tools/csv_to_salary_rules.py`, non chargée) |
| Droits | les 10 modèles persistants ont des lignes `ir.model.access.csv` ; les 3 assistants sont transitoires |
| Record rules | les 7 modèles multi-société ont leur règle `company_id in company_ids` |
| Paramètres | 59 dans `hr_rule_parameters_data.xml`, 0 orphelin ; aucun nombre en dur dans les règles |
| Syntaxe pré-19 (`_sql_constraints`, `attrs=`, `<tree`) | 0 |
| Imports `odoo` dans `lib/` | 0 |
| Méthodes publiques sans test | 0 |
| Messages utilisateur non traduisibles | 0 (`env._`) ; `i18n/fr.po` présent (666 msgid) |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur (ruff, ruff-format, pylint-odoo, règles odoo19) |
| `make test-core` | 483 tests verts, couverture 100 % |
| `make test MODULE=l10n_ga_hr_payroll` (base neuve) | 178 tests, 0 échec, 0 ERROR/CRITICAL ; 5 WARNING (configuration `odoo.conf` du service, `pdfminer.six` absent) : hors module |
| `make upgrade MODULE=l10n_ga_hr_payroll` | 178 tests, 0 échec, 0 ERROR/CRITICAL ; 10 WARNING de même nature |

## C5 — Recette chiffrée

F16 (590 000 → net 514 897) rejoué dans Odoo et sur les données générées (tests 2.2, 2.3, 2.6), parité avec l'oracle ≤ 1 FCFA. Pas de nouvel écart.

## Bloquants et questions pour Alex

- **D-47** : liste des mentions obligatoires du bulletin (point 19 du fichier 09), à valider auprès de l'inspection du travail ou du cabinet. Non bloquant pour l'étape 3.

## Dette technique acceptée

- En-tête `web.external_layout` lu sur la société du jour (comportement standard Odoo) ; identifiants employeur du corps figés (D-48).
- Rendu PDF binaire non exécuté en test automatique ; le HTML transmis à wkhtmltopdf est testé.
- Rapprochement comptable de l'état des charges : étape 3 (D-51).
