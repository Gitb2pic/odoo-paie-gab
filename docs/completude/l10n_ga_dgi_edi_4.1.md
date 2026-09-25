# Complétude — `l10n_ga_dgi_edi`, étape 4.1 (moteur de déclarations)

Date : 25/09/2026 — plan `docs/plans/4.1.md` (go anticipé, D-65 à D-73).

## Score

**24 / 24 éléments attendus présents et testés (100 %)** ; 47 tests Odoo verts sur base neuve et en mise à jour ; 258 tests verts avec la paie et la comptabilité installées ensemble ; installation sur base existante et désinstallation propres.

## C1 — Inventaire attendu / réel

| # | Élément attendu (prompt 04 §4.1, `06` §1, `05` §4, `03` §6.2) | État | Fichier | Test |
|---|---|---|---|---|
| 1 | Manifeste 19.0.2.0.0, dépend de la paie seule (+ `mail`), OPL-1, `countries` | présent | `__manifest__.py` | installation |
| 2 | `l10n_ga.declaration.type` (code, organisme, périodicité, échéance, base de période, générateur, gabarit, validité) | présent | `models/l10n_ga_declaration_type.py` | `test_snapshot` (échéances, périodes, validité), `test_generator_registry` |
| 3 | `l10n_ga.declaration.box` (code, libellé, séquence, cellule, nature, total ; + valeur d'en-tête, rubriques sources, signe) | présent | `models/l10n_ga_declaration_box.py` | `test_generator_registry` |
| 4 | `l10n_ga.declaration` `mail.thread` + `mail.activity.mixin` | présent | `models/l10n_ga_declaration.py` | `test_observer_cron` (activités, messages) |
| 5 | Template Method `action_compute` | présent | idem | `test_fake_generator_template_method` |
| 6 | State `_TRANSITIONS`, `_ensure_state`, gardes | présent | idem | `test_transition_matrix` (36 couples), `test_forbidden_actions` |
| 7 | Snapshot : valeurs stockées, fichiers joints, SHA-256 | présent | idem | `test_validation_freezes_values`, `test_payslip_changed_after_validation`, `test_tampering_detected` |
| 8 | Rectificative `rectified_id` | présent | idem | `test_rectification` |
| 9 | Unicité (société, type, période, hors rectificatives) + `date_to >= date_from` | présent | idem (`UniqueIndex` partiel, D-65) | `test_unique_period`, `test_dates_constraint` |
| 10 | `.line` unique déclaration × case | présent | `models/l10n_ga_declaration_line.py` | `test_frozen_values_locked` |
| 11 | `.detail` (salarié / tiers, `fields.Json`, `payslip_line_ids`) | présent | `models/l10n_ga_declaration_detail.py` | `test_payslip_generator_f16` |
| 12 | Registre `l10n_ga.declaration.generator` + interface `...generator.base` | présent | `models/declaration_generator.py` | `test_registry` |
| 13 | Générateur factice enregistré dans le registre | présent | `tests/common.py` (`FakeGenerator`) | `test_fake_generator_template_method`, `test_checks` |
| 14 | `COMMON_CHECKS` : CNSS, période en double, paramètre manquant, totaux = détails | présent | `models/checks.py` | `test_checks` (1 test par contrôle) |
| 15 | Extension `l10n_ga.check.issue` : `declaration_id`, périmètre (ADR-18) | présent | `models/l10n_ga_check_issue.py` | `test_issue_cascade_and_scope_selection` |
| 16 | Validation refusée si anomalie bloquante (RG15) | présent | `action_validate` | `test_missing_cnss_blocks_validation` |
| 17 | `renderers/xlsx_builder.py` (xlsxwriter) | présent | `renderers/xlsx_builder.py` | `test_new_workbook_without_template`, `test_builder_interface` |
| 18 | `renderers/xlsm_template.py` (openpyxl `keep_vba=True`), même interface, valeurs seulement | présent | `renderers/xlsm_template.py`, `renderers/base.py` | `test_xlsm_keeps_vba_and_writes_values`, `test_declaration_fills_template` |
| 19 | Observer sur la validation des bulletins (ADR-19) | présent | `models/hr_payslip.py` (done, paid, cancel, draft) | `test_payslip_validation_prepares_declaration`, `test_validated_declaration_never_recomputed` |
| 20 | Cron quotidien `_cron_prepare_due_declarations` J-10, activités, « à corriger » ; types d'activité en données | présent | `data/ir_cron_data.xml`, `data/mail_activity_type_data.xml` | `test_cron_*`, `test_cron_record` |
| 21 | Groupes « Déclarant fiscal » (implique paie) et « Responsable » ; seul le déclarant valide / dépose | présent | `security/l10n_ga_dgi_edi_security.xml` | `test_groups_hierarchy`, `test_rights_payroll_user_cannot_validate` |
| 22 | Règles multi-société ; ACL par modèle et groupe | présent | `security/*` | `test_multi_company_rules`, `test_type_configuration_rights` |
| 23 | Vues liste / formulaire / recherche, onglets cases / détails / anomalies / fichiers, tableau de bord des échéances (kanban, calendrier) | présent | `views/*.xml`, `views/menus.xml` | chargement des vues à l'installation (validation d'architecture Odoo) |
| 24 | Rapport PDF (lit les valeurs figées) | présent | `report/report_declaration.xml` | pièce jointe produite dans `test_validation_freezes_values` |

Hors périmètre 4.1 (D-69, D-73) : onglet « quittances » et modèle `l10n_ga.declaration.payment` (4.2) ; `move_line_ids` (étape 5). Écarts d'arborescence par rapport à `06` §1 : `models/l10n_ga_declaration_frozen_mixin.py` (verrou commun lignes/détails) et `renderers/base.py` (interface Builder) ajoutés ; types d'imprimés réels en données à partir de 4.2.

## C2 — Traçabilité

| Exigence | Code | Test |
|---|---|---|
| RG10 type → cases | `declaration.type.box_ids` | `test_generator_registry` |
| RG11 unicité | `_period_unique` (UniqueIndex partiel) | `test_unique_period` |
| RG12 une valeur par case | `_box_unique` | `test_fake_generator_template_method` (1 ligne par case) |
| RG13 détail justifie la case | `.detail`, `TotalsMatchDetails` | `test_totals_match_details`, `test_payslip_generator_f16` |
| RG14 figée, correction par rectificative | frozen mixin, `write`, `action_create_rectification` | `test_frozen_values_locked`, `test_rectification` |
| RG15 validation bloquée | `action_validate` | `test_missing_cnss_blocks_validation` |
| RG16 payée | `action_mark_paid` (manuel, D-69) | `test_full_cycle_by_declarant` |
| RG26 anomalie lot ou déclaration | `scope` + `declaration_id` | `test_issue_cascade_and_scope_selection` |
| ADR-06 figement | `_snapshot`, `sha256` | `test_payslip_changed_after_validation` |
| ADR-07 moteur générique | registre + `payslip` | `test_registry`, `test_payslip_generator_*` |
| ADR-08 pas de XML | Excel + QWeb seulement | — (aucun générateur XML) |
| ADR-10 / ADR-19 Observer + cron | `hr_payslip.py`, `_cron_prepare_due_declarations` | `test_observer_cron` |
| ADR-18 anomalie unique | `_inherit` check.issue | `test_checks` |
| Règle d'or 1 (aucun taux en dur) | codes et paramètres en données ; `ParameterMissing` | `test_parameter_missing` |
| Règle d'or 8 (déclaration figée) | valeurs stockées, PDF sur champs stockés | `test_payslip_changed_after_validation` |
| Règle d'or 9 (arrondi à la ligne) | `_line_values`, détails | `test_fake_generator_template_method` (1 000,6 → 1 001) |
| Règle d'or 10 (valeurs, jamais de formules, `keep_vba`) | renderers | `test_xlsm_*` (aucun `<f>`, VBA identique) |
| Règle d'or 11 (multi-société) | `company_id`, `check_company`, ir.rule | `test_multi_company_rules`, `test_multi_company` |
| Règle d'or 14 (dépendances) | `depends` paie + mail | manifeste |
| Bulletin de décembre payé en janvier | base `payment_date` | `test_december_paid_in_january` |

## C3 — Chasse aux trous

- `TODO|FIXME|…` : aucun ; `NotImplementedError` uniquement dans les interfaces abstraites documentées (patrons 4, 8, 9).
- Fichiers du manifeste tous présents ; aucun XML/CSV non déclaré.
- 5 modèles concrets → 8 lignes d'ACL ; déclaration, ligne, détail avec règle multi-société ; types et cases = configuration partagée (comme `hr.payroll.structure`), sans société.
- Aucun `_sql_constraints`, `attrs=`, `<tree`.
- Nombres littéraux : périodicités 1/3/12 mois (calendrier) ; défauts de champ `due_day=15`, `lead_days=10` (configuration d'imprimé, surchargée par les données de chaque type — pas des taux fiscaux).
- Messages utilisateur via `self.env._()` ; `i18n/fr.po` et `.pot` générés (227 entrées).

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur (ruff, ruff-format, pylint-odoo, règles Odoo 19) |
| `make test-core` | 73 tests d'outillage + 483 tests du noyau, couverture 100 % |
| `make test MODULE=l10n_ga_dgi_edi` | 47 tests, 0 échec, 0 ligne ERROR |
| `make upgrade MODULE=l10n_ga_dgi_edi` | 47 tests, 0 échec, 0 ligne ERROR |
| paie + comptabilité + déclarations ensemble | 258 tests, 0 échec |
| Installation sur base existante (paie + comptabilité), puis désinstallation | `installed` → `uninstalled` ; 9 modèles puis 0 ; sélection `scope` revenue à « Lot de paie » ; cron supprimé |

Avertissements restants : environnement (options `db_*` du fichier de configuration, `http_interface`, bibliothèque `pdfminer` absente), déjà présents aux étapes précédentes.

Incident corrigé : le premier `make upgrade` échouait (`SerializationFailure` sur `ir_cron`) car le cron neuf était dû immédiatement et un worker cron l'exécutait sur la base de test ; première exécution fixée à 2 h le lendemain.

## C5 — Recette chiffrée

Cas F16 (590 000 → net 514 897) validé, puis déclaration calculée par le générateur générique : IRPP 23 195, TCS 13 058, FNH 16 650, CNSS salariale 27 750 — **écart 0** avec les valeurs de l'oracle déjà vérifiées en paie ; total dû = 52 903 ; détail par salarié égal aux cases. Deux salariés → sommes exactes ; bulletin brouillon exclu ; décembre payé le 5 janvier → ID de janvier.

## Bloquants et questions pour Alex

Aucun bloquant pour 4.1. Rappel : D-07 (copie de la V1 `l10n_ga_dgi_edi`) nécessaire **avant 4.4** (gabarits `.xlsm`) et 4.5 (migration).

## Dette technique acceptée

- Rendu PDF en mode test = HTML (comportement d'Odoo, `ir_actions_report.py:1030`) : la pièce jointe de test est `.html` ; en production, `.pdf`.
- Types d'imprimés réels absents tant que 4.2 à 4.4 ne sont pas livrées : l'Observer et le cron n'agissent sur aucun type après installation (voulu).
- Un recalcul remplace toutes les lignes et détails d'une déclaration non figée (simple, volumes mensuels faibles).
