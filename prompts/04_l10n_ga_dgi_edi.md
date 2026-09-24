# Prompt 04 — Module `l10n_ga_dgi_edi` V2 (5 étapes)

> Une étape = une session. Colle l'**en-tête commun** + le bloc de l'étape.

---

## En-tête commun

Tu développes la V2 du module `l10n_ga_dgi_edi` (dépend de `l10n_ga_hr_payroll` uniquement ; `version` `19.0.2.0.0` ; nom technique conservé, ADR-12). Il **ne lit que la paie** : rien de la comptabilité fournisseurs (c'est `l10n_ga_dgi_edi_account`). Relis `CLAUDE.md`, `docs/PROGRESS.md`, `docs/sprint0_verifications_enterprise.md`, ADR-18.

Architecture : `00` ADR-06, 07, 08, 10, 12, 13 ; `02` (séquences clôture mensuelle ID10 et DAS, diagramme d'états) ; `03` RG10-RG16, RG26, §4 et §6.2 ; `04` patrons 4 à 11 ; `05` §4 ; `06` §1 ; `08` F8, F9, F10, F11. Base : `06_declarations_salaires_ID10_ID28_DAS.md`, `02_cadre_legal_et_calendrier.md` (échéances), classeurs `docs/templates_dgi/`.

Attention : le squelette du générateur ID10 dans `04` §4 utilise les codes `IRPP`, `TCS`, `FNH`, `CFP` ; les vrais codes sont ceux du catalogue (`GA_IRPP`, `GA_TCS`, `GA_FNH`, `GA_CFP`…). Lis les codes depuis le catalogue ou un mapping de données, jamais en dur dans deux endroits.

Tu fais **uniquement l'étape demandée** : plan dans `docs/plans/4.X.md`, attente de mon « go », TDD, protocole de complétude.

---

## Étape 4.1 — Moteur de déclarations

**Livrables** :
- `l10n_ga.declaration.type` (code, organisme, périodicité, règle d'échéance, base de période — date de paiement —, clé de générateur, gabarit, dates de validité) et `l10n_ga.declaration.box` (code, libellé, séquence, cellule, nature, total).
- `l10n_ga.declaration` (`mail.thread`, `mail.activity.mixin`) : Template Method `action_compute` ; State `draft → computed → validated → filed → paid`, `cancel`, transitions gardées (`_TRANSITIONS`, `_ensure_state`) ; **Snapshot** à la validation (lignes et détails stockés, fichiers joints, empreinte SHA-256) ; rectificative (`rectified_id`) ; contrainte d'unicité `models.Constraint` (société, type, période, hors rectificatives) ; `date_to >= date_from`.
- `.line` (unique déclaration × case), `.detail` (salarié ou tiers, colonnes `fields.Json`, `payslip_line_ids`).
- Registre `l10n_ga.declaration.generator` + interface `...generator.base` (`_collect`, `_fill`, `_details`, `_checks`).
- Contrôles : chaîne `COMMON_CHECKS` (n° CNSS manquant, période en double, paramètre manquant, totaux = détails) ; extension de `l10n_ga.check.issue` avec `declaration_id` (ADR-18) ; validation refusée s'il reste une anomalie bloquante (RG15).
- Rendus : `renderers/xlsx_builder.py` (`xlsxwriter`) et `renderers/xlsm_template.py` (`openpyxl`, `keep_vba=True`) derrière la même interface Builder ; valeurs uniquement, jamais de formules.
- Observer : surcharge de la validation du lot (nom vérifié au sprint 0) → création/recalcul des déclarations brouillon du mois de paiement ; `ir.cron` quotidien `_cron_prepare_due_declarations()` (J-10, activités `mail.activity` pour le déclarant, activité « à corriger » si anomalie bloquante) ; type d'activité en données.
- Sécurité : groupes « Déclarant fiscal » (implique l'utilisateur paie) et « Responsable » ; règles multi-société ; seul le déclarant valide et marque « déposée ».
- Vues : liste/formulaire/recherche des déclarations, onglets cases / détails / anomalies / quittances, tableau de bord des échéances.

**Tests** : `test_state_machine.py` (toutes les transitions autorisées et interdites, droits), figement (bulletin modifié après validation → déclaration inchangée, empreinte stable), rectificative, unicité, `test_checks.py`, `test_xlsm_macros.py` (gabarit `.xlsm` rempli puis rouvert : projet VBA présent), générateur factice enregistré dans le registre.

---

## Étape 4.2 — ID10, ID28 et quittances multiples (F11)

**Livrables** : générateurs `generators/id10.py` et `id28.py` (lecture `_read_group` des lignes de bulletins **validés**, filtrées sur `l10n_ga_payment_date` dans la période — un bulletin de décembre payé en janvier va dans l'ID10 de janvier ; option société « CFP sur ID28 ») ; types et cases en données XML avec les cellules des gabarits `ID_10_RASS-CFP.xlsx` et `CFP_ID28_*.xlsx` ; rapports PDF QWeb ; détails par salarié ; `l10n_ga.declaration.payment` (plusieurs quittances, nature RS / FNH / CFP / autre, pièce jointe) ; état « payée » quand la somme couvre le total (RG16).

**Tests** : `test_id10.py` (ID10 = Σ bulletins payés du mois, bulletin brouillon exclu, décembre payé en janvier, changement FNH au 17/07/2026, multi-société), ID28, `test_payments.py` (deux quittances, paiement partiel, sur-paiement signalé).

---

## Étape 4.3 — DTS CNSS et CNAMGS (trimestrielles)

**Livrables** : générateurs `dts_cnss.py`, `dts_cnamgs.py` (assiette plafonnée par salarié et par mois, branches PF/AT/AVID), types, cases, détail par salarié, rendu Excel au format attendu par les portails (colonnes documentées dans la base `03` / `06`), PDF récapitulatif, échéances trimestrielles.

**Tests** : trimestre complet, entrée/sortie en cours de trimestre, plafond atteint, totaux DTS = somme des lignes CNSS/CNAMGS des bulletins.

---

## Étape 4.4 — DAS ID19 à ID22, écran « Contrôle DAS », classeurs `.xlsm`

**Prérequis** : gabarits `edi-annexe-ID19/21/23/26.xlsm` de la V1 dans `static/templates/` (depuis `$V1_PATH`). S'ils manquent : **bloquant**, demande-les.

**Livrables** : générateur `das.py` (ID19 récapitulatif, ID20, ID21 détail salariés paginé 39 lignes/feuille, ID22 versements lus sur les quittances de l'année) ; lecture des **valeurs figées** des bulletins et des lignes (F7, F16) et des cumuls d'ouverture (F12) ; hypothèse du point 09-6 (colonne nette des cotisations salariales, classement ID20 sur les rémunérations imposables) en **option société** documentée ; assistant `l10n_ga_das_wizard.py` ; écran « Contrôle DAS » (vue liste partagée des `l10n_ga.check.issue`) ; contrôles DAS (total ID21 = Σ ID10 de l'année, salarié sans NIF/CNSS, codes emploi/niveau manquants) ; remplissage `.xlsm` via le Builder `openpyxl`.

**Tests** : `test_das.py` (DAS = Σ ID10 de l'année, salarié sorti en cours d'année, année de bascule avec cumuls d'ouverture, ID22 = quittances), macros conservées.

---

## Étape 4.5 — Migration des déclarations V1 (ADR-12)

**Prérequis** : code et schéma de la V1 (`$V1_PATH`) et, idéalement, une base V1 anonymisée. Sans eux : **bloquant**.

**Livrables** : `migrations/19.0.2.0.0/pre-migrate.py` (renommage des tables/colonnes V1 : `dgi.id10`, `dgi.id20`, `dgi.id22`, `dgi.dts`, `dgi.edi.declaration`…) et `post-migrate.py` (conversion en `l10n_ga.declaration` figées à l'état « déposée » ou « payée », pièces jointes et quittances rattachées, empreintes SHA-256 recalculées, suppression des anciens modèles) ; port des **11 tests V1** dans `tests/test_v1_ported.py` ; journal de migration.

**Tests** : `make upgrade MODULE=l10n_ga_dgi_edi` sur la base V1 : nombre de déclarations et montants par type identiques avant/après, pièces jointes présentes ; les 11 tests V1 passent.

---

## Fin de CHAQUE étape (obligatoire)

Protocole de complétude `CLAUDE.md` §7 sur le périmètre de l'étape (en C1, inclure pour chaque imprimé : type, cases, générateur, rendu Excel, rendu PDF, contrôles, tests) ; rapport `docs/completude/l10n_ga_dgi_edi_4.X.md` ; commit ; `docs/PROGRESS.md` ; attends mon « go ». Après 4.5 : `prompts/99_completude.md` sur tout le module.
