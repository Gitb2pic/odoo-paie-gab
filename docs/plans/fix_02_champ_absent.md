# Plan — FIX 02 : mise à jour bloquée, champ `l10n_ga_entry_exit_hours` « absent » de `res.company`

Date : 25/09/2026 — module `l10n_ga_hr_payroll` — statut : **en attente du « go » d'Alex**.

## 1. Diagnostic (commandes en lecture seule)

**Cause A — service non redémarré après la modification du Python : CONFIRMÉE.**

| Preuve | Commande | Résultat |
|---|---|---|
| Démarrage du processus qui a fait la mise à jour | `journalctl -u odoo19 -o short-iso \| grep -m1 'python3\[436583\]'` | processus **436583** démarré le **25/09 à 15:32:04** |
| Modification du Python (FIX 01) | `stat -c '%y' l10n_ga_hr_payroll/models/res_company.py` | **15:44:39** (vue modifiée à la même seconde) |
| Mise à jour depuis l'interface | `journalctl -u odoo19 --since 15:40` | 15:48:46 « Loading module l10n_ga_hr_payroll » par le processus **436583**, puis 15:48:49 `ParseError … Le champ "l10n_ga_entry_exit_hours" n'existe pas dans le modèle "res.company"` |
| Conclusion | — | le processus (15:32) est **plus ancien** que le code (15:44) : il a lu la nouvelle vue sur le disque, mais pas le nouveau Python |

**Cause B — champ mal nommé ou sur un autre modèle : écartée.** `grep -rn l10n_ga_entry_exit l10n_ga_hr_payroll/` → défini sur `res.company` (`models/res_company.py:35`), même orthographe dans la vue (`views/res_company_views.xml:22`) et dans le bulletin (`models/hr_payslip.py:209`).

**Cause C — fichier Python non chargé : écartée.** `models/__init__.py:20` importe `res_company` ; `__init__.py` importe `models` ; `ast.parse` du fichier sans erreur ; la vue ne dépend d'aucun module hors `depends`. Preuve supplémentaire : `make test MODULE=l10n_ga_hr_payroll` (processus neuf, base neuve) installe cette vue et passe ses 188 tests (FIX 01).

**État actuel de la base `odoo19`** (unique base du service, instance `labpaiega.labtools.tech`) : le service a été redémarré à **16:14:58** (processus 449714), `l10n_ga_hr_payroll` est en **19.0.1.6.4 installé** et la colonne `res_company.l10n_ga_entry_exit_hours` existe (`information_schema`) : la mise à jour a réussi après le redémarrage. Aucune correction de code n'est nécessaire.

## 2. Correction (cause A)

- Aucun changement de code ni de vue (le champ reste dans la vue).
- Vérification : `make demo MODULE=l10n_ga_hr_payroll` (processus neuf `-u … --stop-after-init`, puis redémarrage), puis contrôle de l'onglet « Gabon — Paie et fiscalité » de la société (le champ « Entrée / sortie en cours de mois » y figure).

## 3. Garde-fous

1. **Makefile** : `make upgrade` utilise déjà un processus neuf sur une base de test ; `make demo` lance un processus neuf `-u MODULE --stop-after-init` **puis** redémarre le service. Ajout d'une cible `make update-demo MODULE=…` explicite (alias documenté de `demo` : processus neuf, jamais le bouton de l'interface) et d'un commentaire dans le `Makefile`.
2. **`CLAUDE.md` §5** : règle « Après toute modification d'un fichier `.py`, redémarrer le service Odoo avant de mettre à jour le module (`make demo`) ; ne jamais utiliser le bouton « Mettre à jour » de l'interface pour du code modifié. »
3. **Test** : `make test MODULE=l10n_ga_hr_payroll` sur base neuve installe la vue sans erreur — il ne pouvait pas attraper l'incident, qui ne vient ni du code ni de la vue mais d'un processus ancien (le rapport l'explique).
4. **C3 automatique** : `tools/check_view_fields.py`, lancé par `make lint` (pre-commit) : chaque `<field name="l10n_ga_…">` d'une vue du dépôt doit être défini en Python sur le modèle ciblé (modèle de la vue ou modèle hérité), dans le module ou l'une de ses dépendances du dépôt ; tests dans `tools/tests/`.
5. **Explication pour Alex** : `docs/incidents/2026-09-25_champ_absent_res_company.md`.

## 4. Commits

`fix(l10n_ga_hr_payroll): …` n'a pas d'objet (aucun code à corriger) : un seul commit `chore(repo): garde-fou redémarrage avant mise à jour` (Makefile, CLAUDE.md, script de contrôle, incident), puis `chore(l10n_ga_hr_payroll): complétude FIX 02`.
