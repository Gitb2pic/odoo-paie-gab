# Prompt 06 — Module `l10n_ga_hr_payroll_migration` (reprise jetable)

---

Tu développes le module ponctuel `l10n_ga_hr_payroll_migration` (dépend de `l10n_ga_hr_payroll` et `l10n_ga_dgi_edi` ; **jamais** de `hr_payroll_gb`). Il est installé le temps de la bascule puis désinstallé ; les cumuls d'ouverture restent (portés par `l10n_ga_hr_payroll`).

**Prérequis** : schéma réel des tables `hr_payroll_gb` sur la base du client (sprint 0, point 8) — dump anonymisé ou sortie de `\d` pour chaque table. Sans lui : **bloquant**, demande-le avant de coder la table de correspondance.

Relis `CLAUDE.md`, `docs/PROGRESS.md`. Architecture : `05` §6 ; `08` F12 ; `04` §14 (Data Mapper) ; `01` §7 (bascule) ; `07_benchmark_hr_payroll_gb_vs_v2.md` (codes, défauts B1, B2, M3, M4 à expliquer dans le rapprochement) ; `00` ADR-11, ADR-14.

Plan dans `docs/plans/6.md`, attente de mon « go », TDD.

## Livrables

- `l10n_ga.migration.map` (source, code source, cible, code cible, règle de conversion) + données initiales : rubriques freelance → `GA_*`, types de congés, catégories → grades, champs salarié et société (NINEA, CMU et champs étrangers explicitement ignorés).
- Assistant `l10n_ga_migration_wizard.py` : détection des tables par `information_schema`, lecture **SQL en lecture seule**, étapes rejouables et idempotentes : salariés et versions (situation, enfants, n° CNSS, mode de paiement), grades, prêts en cours avec échéances restantes, variables du mois en cours, `l10n_ga.ytd.opening` (brut, imposable, IRPP, TCS, CNSS, gratifications exonérées, période couverte).
- Tout code non mappé = anomalie de reprise (jamais ignoré en silence).
- `report/report_migration_reconciliation.xml` : cumuls repris = cumuls des bulletins `hr_payroll_gb` de l'année, par salarié et par rubrique ; bulletin du dernier mois recalculé en V2 comparé ligne à ligne, écarts classés (défaut connu B1/B2/M3/M4 ou écart inexpliqué).
- Procédure de désinstallation documentée dans `README.md` du module.

## Tests (`tests/test_migration.py`)

Base fictive créant des tables au schéma `hr_payroll_gb` (dans le test, par SQL) : reprise complète, relance sans doublon, code non mappé → anomalie, prêt en cours → échéancier restant exact, cumuls d'ouverture → régularisation IRPP juste en décembre, rapprochement sans écart sur un jeu propre.

## Fin obligatoire

Protocole de complétude `CLAUDE.md` §7 ; rapport `docs/completude/l10n_ga_hr_payroll_migration.md` ; puis `prompts/99_completude.md` en mode **dépôt complet** (les 5 modules installés ensemble sur une base neuve, `--test-tags` des 5 modules) ; commit ; `docs/PROGRESS.md`.
