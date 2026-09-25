# CLAUDE.md — Paie Gabon & déclarations DGI (Odoo 19 Enterprise, V2)

> Fichier mémoire permanent de Claude Code, à la racine du dépôt `/home/ubuntu/odoo/extra-addon` (VPS Ubuntu, Odoo 19 Enterprise déjà installé ; détails dans `docs/environnement_vps.md`, rempli au sprint 0).
> Il est lu à chaque session. Les prompts d'étape (`prompts/0X_*.md`) disent QUOI coder ; ce fichier dit COMMENT.

## 1. Mission

Tu développes **de zéro** les addons Odoo 19 Enterprise de paie gabonaise et de déclarations fiscales/sociales DGI, **un module à la fois, une étape à la fois**, en suivant l'architecture figée dans `docs/architecture/`. Tu ne réutilises aucun code du module freelance `hr_payroll_gb` ni de la V1 (sauf gabarits `.xlsm` et tests V1 à porter, cités explicitement).

Ordre de développement (ne jamais sauter une étape) :

| # | Module | Rôle |
|---|---|---|
| 0 | socle du dépôt | outillage, vérifications Enterprise |
| 1 | `l10n_ga_hr_payroll` | noyau fiscal pur + paie Gabon complète |
| 2 | `l10n_ga_hr_payroll_account` | imputations SYSCOHADA (auto_install) |
| 3 | `l10n_ga_dgi_edi` | moteur de déclarations, ID10, ID28, DTS, DAS ID19-ID22, migration V1 |
| 4 | `l10n_ga_dgi_edi_account` | périmètre V1.0 : ID18, ID27, ID23, ID24, ID26 |
| 5 | `l10n_ga_hr_payroll_migration` | reprise jetable depuis `hr_payroll_gb` |

## 2. Sources de vérité (par ordre de priorité)

1. `docs/sprint0_verifications_enterprise.md` — résultats de la lecture du code Enterprise (sprint 0). **Remplace** toute hypothèse marquée 🔒 dans l'architecture.
2. `docs/base_connaissance/` — fiscalité : `parametres_fiscaux_gabon_2026.yaml` (taux datés), `calcul_paie_gabon_reference.py` (calculateur validé = oracle des tests), `04_impots_sur_salaires_*.md` §7 (algorithme) et §8 (exemples chiffrés), `05_elements_de_remuneration.md` (matrice des rubriques), `06_declarations_*.md`, `09_points_a_verifier.md` (hypothèses par défaut).
3. `docs/architecture/` — `00_INDEX` (ADR-01 à ADR-17), `01` (modules, couches), `02` (UML), `03` (RG01-RG30, MCD/MLD/MPD), `04` (16 patrons + squelettes), `05` (points d'extension exacts), `06` (arborescence, tests, CI), `08` (F1-F16).
4. Code source Odoo : Community `$ODOO_PATH` et Enterprise `$ENTERPRISE_PATH`. **Ne réponds jamais de mémoire sur une API Odoo** : ouvre le fichier, cite `chemin:ligne` dans tes notes.

En cas de contradiction entre deux sources : ne tranche pas seul. Écris le conflit dans `docs/decisions/ouvertes.md` (contexte, options, recommandation) et demande à Alex.

## 3. Règles d'or (non négociables)

1. **Aucun taux, plafond ni barème en dur** — ni dans le noyau, ni dans les règles salariales, ni dans les générateurs. Tout vient de `hr.rule.parameter` (valeurs datées) générés depuis le YAML par `tools/yaml_to_rule_parameters.py`.
2. **`ga_fiscal_core` n'importe jamais `odoo`** (vérifié par un test AST). Dataclasses `frozen=True`, fonctions pures, entrées = nombres + `FiscalParams`.
3. **Une seule règle `NET`**, jamais redéfinie ni dupliquée (défaut B1). L'arrondi espèces agit après `NET` (`GA_ROUND_PREV`, `GA_ROUND`, `GA_NET_PAY`).
4. **Ne jamais redéfinir `wage` ni `number`** (défauts M8, M9). Le minimum conventionnel est un contrôle.
5. Données fiscales personnelles sur **`hr.version`**, jamais en champ stocké sur `hr.employee` (ADR-05).
6. Variables du mois = **`hr.payslip.input`** ; indemnités contractuelles = lignes datées (ADR-16), jamais un champ par rubrique.
7. Exonérations **par ligne** dans le noyau, plafonds par **groupe** via registre `SOCIAL_CAPS` / `TAX_CAPS` (ADR-17).
8. **Bulletin figé** (F7) et **déclaration figée** (ADR-06) : valeurs stockées à la validation, jamais de `compute` non stocké pour ce qui est imprimé ou déclaré. Correction = rectificative.
9. Arrondi **au franc, à la ligne** (`float_round(x, precision_digits=0)`), jamais sur les totaux intermédiaires.
10. Excel : `xlsxwriter` pour les états neufs ; `openpyxl.load_workbook(..., keep_vba=True)` pour les classeurs DGI `.xlsm`. On écrit des **valeurs, jamais de formules**. **Aucune génération XML** (ADR-08).
11. Multi-société : `company_id` obligatoire sur les nouveaux modèles métier, `check_company=True` sur les Many2one, règles d'enregistrement `company_id in company_ids`.
12. Aucune dépendance à `hr_payroll_gb`. Le module de reprise le lit en **SQL lecture seule** uniquement.
13. Point fiscal non tranché (fichier 09) = **paramètre daté ou option société** avec valeur par défaut documentée — jamais un choix silencieux dans le code.
14. Aucun module Gabon ne dépend d'un module « plus haut » (règle de dépendance du fichier 01 §3).

## 4. Conventions Odoo 19

- Syntaxe : `models.Constraint(...)` (plus de `_sql_constraints`), `@api.model_create_multi`, `fields.Json`, `_read_group(domain, groupby, aggregates)`, vues `<list>` (plus de `<tree>`), `invisible="..."` / `readonly="..."` directs (plus d'`attrs`), `hr.version` porte les données datées.
- Nommage : champs/méthodes `l10n_ga_*` sur les modèles standard ; nouveaux modèles `l10n_ga.*` ; règles `GA_*` ; paramètres `l10n_ga_<sujet>_<nature>` ; xml_id explicites et stables.
- Libellés en français dans le code, `i18n/fr.po` généré ; noms techniques en anglais.
- Manifeste : `version` `19.0.x.y.z`, `license: 'OPL-1'`, `countries: ['ga']`, chaque fichier de `data` existe réellement.
- Sécurité : une ligne `ir.model.access.csv` par nouveau modèle et par groupe ; montants de salaire invisibles hors groupes paie.
- Qualité : `ruff`, `pylint-odoo` sans erreur ; couverture ≥ 90 % sur `lib/ga_fiscal_core`.
- Tests Odoo : `TransactionCase` / `tagged('post_install', '-at_install')`, données de test créées dans `setUpClass`, jamais dépendantes de la base de démo.

## 5. Commandes (voir `Makefile`, créé au sprint 0 sur l'installation Odoo existante du VPS)

Sur le VPS : ne jamais toucher aux bases existantes (bases de test préfixées `test_ga_`), ne jamais arrêter le service Odoo pour lancer des tests, ne jamais modifier les autres modules présents dans `extra-addon`.
Après toute modification d'un fichier `.py`, **redémarrer le service Odoo avant de mettre à jour le module** (`make demo` / `make update-demo` : processus neuf `-u … --stop-after-init`, puis redémarrage) ; **ne jamais utiliser le bouton « Mettre à jour » de l'interface pour du code modifié** : le service en cours garde l'ancien Python et refuse les vues qui citent de nouveaux champs (incident FIX 02 du 25/09/2026).
Seule exception (décision D-09) : la base de démonstration `odoo19` d'Alex reçoit les modules `l10n_ga_*` **validés**, uniquement via `make demo MODULE=...` (installation ou mise à jour, puis redémarrage du service) ; jamais de tests ni de données de test dans `odoo19`.

```bash
make lint                          # pre-commit run --all-files
make test-core                     # pytest l10n_ga_hr_payroll/lib --cov (sans Odoo, < 1 s)
make test MODULE=l10n_ga_hr_payroll   # base neuve, -i MODULE --test-tags /MODULE --stop-after-init
make upgrade MODULE=...            # -u MODULE sur une base existante (test de mise à jour)
make demo MODULE=...               # installe / met à jour un module validé dans la base de démo odoo19 (D-09)
make update-demo MODULE=...        # alias de demo : processus neuf puis redémarrage (jamais le bouton de l'interface)
```

## 6. Déroulé d'une session (obligatoire)

1. **Lire** : ce fichier, `docs/PROGRESS.md`, le prompt de l'étape, puis les sections d'architecture qu'il cite. Ouvrir le code Odoo concerné.
2. **Planifier** : écrire `docs/plans/<etape>.md` (fichiers à créer, modèles/champs, tests, points 🔒 touchés, risques). **Présenter le plan à Alex et attendre son « go »** avant de coder.
3. **Coder en TDD** : test d'abord pour le noyau, les règles, les contraintes et les générateurs ; puis le code ; petits pas.
4. **Commits** atomiques, Conventional Commits, scope = module : `feat(l10n_ga_hr_payroll): ...`, `test(...)`, `fix(...)`.
5. **Protocole de complétude** (§7) — obligatoire, jamais sauté.
6. **Mettre à jour** `docs/PROGRESS.md` (étape, état, score de complétude, bloquants, prochaine étape).

## 7. Protocole de complétude (fin de CHAQUE développement)

Une étape n'est **terminée** que lorsque ce protocole passe entièrement. Tu ne te contentes pas de lister les manques : **tu les complètes**, puis tu relances, jusqu'à zéro manque (ou bloquant documenté).

**C1 — Inventaire attendu / réel.** Construis le tableau des éléments attendus pour l'étape (arborescence `06` §1, manifeste `05`, modèles `03` §6, champs `05` §2.2, règles `05` §2.4, tests `06` §1 et §3, éléments listés dans le prompt d'étape). Pour chacun : présent / partiel / absent, avec le chemin du fichier.

**C2 — Traçabilité.** Matrice exigence → code → test pour chaque RG (fichier 03), F (fichier 08), ADR (fichier 00) et règle d'or du périmètre. Toute exigence sans test = manque.

**C3 — Chasse aux trous (automatique).** Lance et corrige :
- `grep -rnE "TODO|FIXME|XXX|HACK|NotImplementedError|pass\s*$|\.\.\.\s*$"` sur le module (hors interfaces abstraites documentées) ;
- fichiers cités dans `__manifest__.py` absents, ou fichiers XML/CSV présents mais non déclarés ;
- modèles sans ligne dans `ir.model.access.csv`, modèles multi-société sans record rule ;
- champs référencés dans une vue/rapport mais inexistants sur le modèle (automatique pour les champs `l10n_ga_*` des vues : `tools/check_view_fields.py`, lancé par `make lint`) ;
- nombres littéraux dans `amount_python_compute`, les générateurs ou le noyau (autres que 0, 1, 100 et index) → doivent venir d'un paramètre ;
- imports `odoo` dans `lib/ga_fiscal_core` ;
- `_sql_constraints`, `attrs=`, `<tree` (syntaxe pré-19) ;
- méthodes publiques sans test ;
- libellés non traduisibles (`_()` manquant sur les messages utilisateur).

**C4 — Exécution.** `make lint` = 0 erreur ; `make test-core` vert avec couverture ≥ 90 % ; `make test MODULE=<module>` vert sur **base neuve** ; `make upgrade MODULE=<module>` sans erreur ni warning bloquant ; installation puis désinstallation propres si le module le permet. Aucun test `skip`, `expectedFailure` ou commenté pour « faire passer ».

**C5 — Recette fonctionnelle.** Rejoue les cas chiffrés du périmètre (exemples du fichier 04 §8 de la base, cas 590 000 → net 514 897 du fichier 08 F16, jeux prioritaires du fichier 06 §3) et compare au calculateur `calcul_paie_gabon_reference.py` : écart ≤ 1 FCFA par ligne.

**C6 — Complétion.** Pour chaque manque de C1 à C5 : code-le, teste-le, relance C3 à C5. Boucle jusqu'à zéro manque. Si un manque dépend d'une information absente (point 🔒 non vérifiable, fichier V1 manquant, décision fiscale), classe-le **Bloquant**, avec la question précise à poser à Alex — ne le contourne pas par un bouchon silencieux.

**C7 — Rapport.** Écris `docs/completude/<module>_<etape>.md` :
- score = éléments présents et testés / éléments attendus (%) ;
- tableaux C1 et C2 finaux ;
- résultats C4 (sorties résumées des commandes, couverture) ;
- écarts C5 ;
- bloquants et questions pour Alex ;
- dette technique acceptée (avec justification).
Puis commit `chore(<module>): complétude étape <n>` et résumé de 10 lignes max dans le chat.

## 8. Ce que tu ne fais jamais

- Coder une étape suivante sans « go » d'Alex.
- Modifier l'architecture en silence : tout écart = ADR dans `docs/adr/ADR-XX-*.md` + validation d'Alex.
- Inventer un nom de champ, de méthode ou de variable Enterprise : vérifie dans `$ENTERPRISE_PATH`.
- Écrire un secret, un mot de passe ou des données réelles de salariés dans le dépôt.
- Marquer une étape terminée avec un test rouge, sauté ou supprimé.

## 9. Économie de tokens
- Ne lis jamais docs/sources_pdf/ ni docs/architecture/diagrammes_svg/ sauf si je te le demande : la base de connaissance en Markdown les résume déjà.
- Lis seulement les sections d'architecture citées par le prompt d'étape, pas les fichiers entiers.
