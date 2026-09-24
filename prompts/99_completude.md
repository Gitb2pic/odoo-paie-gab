# Prompt 99 — Complétude du code (réutilisable)

> À lancer à la fin de chaque étape, de chaque module, ou avant une livraison.
> Remplace `<PERIMETRE>` par : `étape 2.3`, `module l10n_ga_hr_payroll`, ou `dépôt complet`.

---

Mode **complétude** sur le périmètre `<PERIMETRE>`. Tu ne développes aucune fonctionnalité nouvelle hors de ce périmètre : tu vérifies que ce qui devait être codé l'est entièrement, testé et conforme à l'architecture, et **tu complètes tout ce qui manque**.

Relis `CLAUDE.md` (§3 règles d'or, §7 protocole), `docs/PROGRESS.md`, les prompts d'étape du périmètre (`prompts/0X_*.md`), `docs/sprint0_verifications_enterprise.md`, les ADR acceptés et `docs/decisions/ouvertes.md`.

## 1. Construire la liste de l'attendu

À partir des prompts d'étape et de l'architecture (`05` manifestes et extensions, `06` §1 arborescence et §3 jeux de tests, `03` RG et contraintes §6, `08` F1-F16, `00` ADR), dresse la liste exhaustive des éléments attendus : fichiers, modèles, champs, contraintes, règles salariales, paramètres, données, vues, menus, droits, rapports, générateurs, cases, crons, tests.

## 2. Comparer à l'existant

Tableau `élément | attendu (source) | état : présent / partiel / absent | fichier | test associé`. « Partiel » = présent sans test, ou test qui ne vérifie pas le comportement métier, ou bouchon.

## 3. Chasse aux trous

Exécute et exploite les vérifications C3 de `CLAUDE.md` §7 (TODO/stubs, manifeste ↔ fichiers, droits, record rules, champs de vues, nombres en dur, imports `odoo` dans le noyau, syntaxe pré-19, messages non traduisibles, méthodes publiques non testées). Ajoute :
- chaque paramètre utilisé par le code existe dans le YAML **et** dans `hr_rule_parameters_data.xml` (et inversement : aucun paramètre orphelin) ;
- chaque rubrique du catalogue a un traitement social et fiscal, et un compte (ou « sans écriture » justifié) ;
- chaque type de déclaration a cases, générateur, rendus, contrôles et tests ;
- chaque point 🔒 utilisé est confirmé dans `sprint0_verifications_enterprise.md` ;
- chaque hypothèse du fichier 09 touchée est un paramètre ou une option documentée.

## 4. Exécuter

`make lint` ; `make test-core` (couverture ≥ 90 %) ; `make test MODULE=<chaque module du périmètre>` sur base neuve ; `make upgrade` ; pour `dépôt complet` : installation des 5 modules ensemble puis `--test-tags /l10n_ga_hr_payroll,/l10n_ga_hr_payroll_account,/l10n_ga_dgi_edi,/l10n_ga_dgi_edi_account,/l10n_ga_hr_payroll_migration`.

## 5. Recette chiffrée

Rejoue les cas de référence du périmètre et compare au calculateur `calcul_paie_gabon_reference.py` (≤ 1 FCFA par ligne) ; pour les déclarations : ID10 = Σ bulletins payés du mois, DAS = Σ ID10 de l'année, DTS = Σ cotisations du trimestre.

## 6. Compléter

Pour chaque élément absent ou partiel : écris le code et le test, relance 3 à 5. **Boucle jusqu'à zéro manque.** Ce qui dépend d'une information que tu n'as pas devient un **bloquant** avec une question précise pour Alex ; jamais de bouchon silencieux, jamais de test désactivé.

## 7. Rapport

`docs/completude/<perimetre>.md` : score (présent et testé / attendu), tableaux finaux, sorties résumées des commandes et couverture, écarts de recette, bloquants et questions, dette acceptée. Commit `chore(<module|repo>): complétude <perimetre>`, mise à jour de `docs/PROGRESS.md`, résumé de 10 lignes max dans le chat. Puis attends mon « go ».
