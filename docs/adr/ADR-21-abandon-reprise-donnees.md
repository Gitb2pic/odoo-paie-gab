# ADR-21 — Abandon de la reprise des données (étape 6) et de la migration V1 (4.5)

- Statut : **accepté** (Alex, 27/09/2026 : « il n'y a pas de données de paie réelles, supprime cette action »)
- Remplace : ADR-11 / ADR-12 / ADR-14 pour leur partie reprise ; décision D-112.

## Contexte
Le module `l10n_ga_hr_payroll_migration` devait reprendre salariés, prêts et cumuls depuis `hr_payroll_gb`,
et l'étape 4.5 convertir les déclarations de la V1 de `l10n_ga_dgi_edi`. Aucune base ne contient de données
de paie réelles à conserver.

## Décision
Le module de reprise n'est pas développé ; l'étape 4.5 est abandonnée. Les outils déjà livrés couvrent un
démarrage éventuel en cours d'année : import Excel (F3), cumuls d'ouverture (F12), saisie des prêts (F1).

## Conséquences
Le dépôt compte 4 modules ; la complétude finale (`prompts/99_completude.md`) porte sur ces 4 modules.
La V1 (`~/supergel-compta`) ne sert plus qu'à récupérer les gabarits `.xlsm` (D-87).
