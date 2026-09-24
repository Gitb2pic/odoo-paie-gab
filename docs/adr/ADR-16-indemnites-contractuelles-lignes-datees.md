# ADR-16 — Indemnités contractuelles en lignes datées (`hr.salary.attachment`)

- **Statut** : proposé (sprint 0, 24/09/2026) — à valider par Alex
- **Origine** : `CLAUDE.md` §3 règle 6 cite ADR-16, absent de `docs/architecture/00_INDEX` (voir `docs/decisions/ouvertes.md` D-02). Rédigé à partir de cette règle et du point 9 de `docs/sprint0_verifications_enterprise.md`.

## Contexte

Les indemnités contractuelles fixes (logement, transport, responsabilité, sujétion…, fichier `05_elements_de_remuneration.md` de la base) varient d'un salarié à l'autre et changent dans le temps. Le module freelance `hr_payroll_gb` les stockait en **un champ par rubrique** sur la fiche, sans historique (benchmark `07`). Deux pistes en Odoo 19 : champs sur `hr.version` (un par rubrique), ou lignes datées génériques.

Le sprint 0 établit que `hr.salary.attachment` (« Salary Adjustment », Enterprise) :
- pousse une entrée `hr.payslip.input` d'un type `available_in_attachments` sur chaque bulletin dont la période recoupe `date_start`–`date_end` (`E/hr_payroll/models/hr_payslip.py:296-311`) ;
- ne connaît ni gain ni retenue : **la règle salariale qui lit l'entrée fixe le signe et la catégorie** → un gain est accepté ;
- gère durée illimitée, dates, historique (`mail.thread`), montant fixe par bulletin.

## Décision

1. Chaque indemnité contractuelle = un **type d'entrée** `hr.payslip.input.type` Gabon (`available_in_attachments = True`, `country_id` = Gabon) + une **règle** `GA_*` qui le lit (catégorie, indicateurs d'assiette sociale/fiscale portés par la règle, ADR-17).
2. L'attribution à un salarié = un `hr.salary.attachment` **daté** (`duration_type = 'unlimited'`, `date_start`, `date_end` à la fin du droit). Une revalorisation = clôture de la ligne + nouvelle ligne datée.
3. **Aucun champ par rubrique** sur `hr.version` ni `hr.employee`.
4. Proratisation (entrée/sortie en cours de mois, absences non rémunérées) : faite par la **règle** via `l10n_ga_prorate` (voir ADR-19, règle courante exposée), jamais en modifiant le montant de la ligne.
5. Les variables du mois (primes ponctuelles, heures) restent des `hr.payslip.input` saisies/importées (F3) — pas des `hr.salary.attachment`.

## Conséquences

- Historique et audit natifs ; import CSV standard ; écran standard « Ajustements de salaire ».
- `record_payment()` n'a pas de sens pour une indemnité illimitée (pas de total) : sans effet, vérifié par test.
- Le libellé de contrainte standard (« montant strictement positif… retenue ») peut surprendre : une indemnité n'est jamais négative, la contrainte reste valable ; libellé d'aide ajouté sur la vue Gabon.
- Rattachement au salarié (`employee_ids`) et non à la version : acceptable (lignes datées indépendantes des versions) ; le contrôle F8 signale une ligne active hors période de contrat.
- Le module de reprise (étape 6) convertit les champs « par rubrique » de `hr_payroll_gb` en lignes datées.

## Alternatives écartées

- Un champ par rubrique sur `hr.version` : pas d'historique propre par rubrique, schéma à modifier pour chaque nouvelle indemnité, défaut du freelance.
- Modèle maison `l10n_ga.version.allowance` : duplique un mécanisme standard qui convient.
