# Complétude — `l10n_ga_hr_payroll`, étape 2.2 (squelette du module et données)

Date : 24/09/2026 — plan : `docs/plans/2.2.md` (« go avec recommandation », D-15 à D-17 décidés).

## Score

**19 / 19 éléments attendus présents et testés = 100 %.** Aucun bloquant. Deux questions non bloquantes pour Alex (fin du document).

## C1 — Inventaire attendu / réel

| # | Élément attendu (prompt 2.2, `05` §2.1-2.4, `06` §1, F4/F6/F14) | État | Emplacement |
|---|---|---|---|
| 1 | `__manifest__.py` (19.0.x.y.z, OPL-1, `countries`, fichiers `data` existants) | présent | `l10n_ga_hr_payroll/__manifest__.py` |
| 2 | `__init__.py` | présent | `l10n_ga_hr_payroll/__init__.py`, `models/__init__.py` |
| 3 | `security/` (groupes, `ir.model.access.csv` vide prêt) | présent | groupes `hr_payroll` réutilisés (sprint 0 point 10) ; `security/ir.model.access.csv` (en-tête), `security/l10n_ga_hr_payroll_security.xml` |
| 4 | `i18n/` | présent | `i18n/l10n_ga_hr_payroll.pot`, `i18n/fr.po` (139 entrées, `make i18n`) |
| 5 | `tools/yaml_to_rule_parameters.py` idempotent + test de régénération | présent | `tools/yaml_to_rule_parameters.py`, `tools/tests/test_yaml_to_rule_parameters.py` |
| 6 | `data/hr_rule_parameters_data.xml` (valeurs datées, codes `l10n_ga_*`) | présent | 50 paramètres, 56 valeurs datées |
| 7 | `data/catalogue_rubriques_ga.csv` (~60 rubriques, colonne `source`) | présent | 62 lignes, 17 colonnes |
| 8 | `tools/csv_to_salary_rules.py` → `data/hr_salary_rule_data.xml` | présent | + `data/hr_payslip_input_type_data.xml` |
| 9 | `NET`, `GROSS`, `BASIC` standard réutilisées / conformes | présent | lignes `standard` du catalogue, formules de `E/hr_payroll/data/hr_salary_rule_data.xml:10-123` |
| 10 | Type de structure « Gabon : Employé » | présent | `data/hr_payroll_structure_type_data.xml` |
| 11 | Structure « Gabon — Employé » | présent | `data/hr_payroll_structure_data.xml` (`rule_ids = []`) |
| 12 | Catégories | présent | `data/hr_salary_rule_category_data.xml` (`GA_AIK`, `GA_SOC`, `GA_TAX`, `GA_EMPLOYER`, `GA_CASH`) |
| 13 | Types d'entrée dont `GA_LOAN` | présent | 59 types (`GA_LOAN` non `available_in_attachments`) |
| 14 | Prestations `GA_HS_J/N/DIM/FER`, `GA_MAT`, `GA_AT`… | présent | `data/hr_work_entry_type_data.xml` (16 types) |
| 15 | 12 types d'absence F4 avec indicateur rémunéré / non rémunéré / CNSS | présent | `data/hr_leave_type_data.xml`, champ `hr.work.entry.type.l10n_ga_pay_mode` |
| 16 | Séquence des prêts | présent | `data/ir_sequence_data.xml` |
| 17 | `l10n_ga_irpp_min_withholding` = 0 (F14) | présent | `rule_parameter_irpp_min_withholding_20000101` |
| 18 | `test_rule_codes_unique.py` (RG22) | présent | `tests/test_rule_codes_unique.py` (9 tests) |
| 19 | Installation sur base neuve | présent | `make test` (18 tests Odoo), `make upgrade`, désinstallation |

Éléments ajoutés par décision : champs de traitement de `hr.salary.rule` (D-16, `models/hr_salary_rule.py`) ; `ga_fiscal_core/param_codes.py` (table des codes partagée avec l'adaptateur de 2.3) ; `ga_fiscal_core/treatment.py` (vocabulaire partagé générateur / contrainte) ; `make i18n` ; `conftest.py` racine (collecte pytest des tests purs dans un addon).

## C2 — Traçabilité exigence → code → test

| Exigence | Code | Test |
|---|---|---|
| RG05 (une rubrique = une structure, une catégorie) | `tools/csv_to_salary_rules.py` (`struct_id`, `category_id` par règle) | `test_rules_attached_to_ga_structure_with_treatment` |
| RG06 (valeur datée : dernière `date_from` ≤ date) | `param_codes.dated_values`, XML généré | `test_one_value_per_effective_date`, `test_parity_generated_values_vs_yaml_loader` (4 dates), Odoo `test_dated_values_rg06` |
| RG22 (code unique par structure) | validation `load_catalogue` | `test_codes_unique`, `test_invalid_catalogue_rejected[double]`, Odoo `test_codes_unique_per_structure` |
| F4 (12 absences, indicateur) | `hr_work_entry_type.py`, `hr_work_entry_type_data.xml`, `hr_leave_type_data.xml` | Odoo `test_twelve_absences_with_pay_indicator`, `test_overtime_work_entry_types_without_rate` |
| F6 (catalogue, traitement, source, NET non redéfini) | `catalogue_rubriques_ga.csv`, `csv_to_salary_rules.py` | `test_every_rubric_has_treatment_and_source`, `test_standard_rules_only_basic_gross_net`, Odoo `test_every_rule_has_social_and_tax_treatment` |
| F14 (seuil IRPP = 0) | paramètre `l10n_ga_irpp_min_withholding` | `test_f14_min_withholding_is_zero` (pytest et Odoo) |
| ADR-16 (indemnités = types `available_in_attachments`) | colonne `input_kind` | `test_input_types` (pytest et Odoo) |
| ADR-17 (groupes connus du registre) | `treatment.check_treatment`, contrainte `_check_l10n_ga_treatment` | `test_cap_groups_known_by_core`, `test_invalid_treatments`, Odoo `test_constraint_rejects_unknown_group`, `test_constraint_rejects_capped_without_group` |
| Sprint 0 point 6 (`GA_LOAN` jamais dans les ajustements) | validation du catalogue | `test_loan_not_in_attachments`, `test_invalid_catalogue_rejected[GA_LOAN]`, Odoo `test_input_types` |
| Sprint 0 point 11 (littéraux Python, préfixe, pas de `inf`) | `yaml_to_rule_parameters.render` | `test_values_are_python_literals_without_inf`, `test_codes_prefixed_unique_and_country` |
| Sprint 0 point 12 / défaut B1 (NET unique, pas de copie de la structure par défaut) | `rule_ids = []`, une seule ligne `NET` | Odoo `test_single_net_rule`, `test_default_structure_rules_not_copied` |
| Règle d'or 1 (aucun taux en dur) | formules génériques `inputs[...]` ; tout taux dans `hr.rule.parameter` | `test_no_numeric_literal_in_formulas`, `test_every_fiscal_field_has_a_code` |
| Règle d'or 3 (NET unique) | catalogue | `test_one_rule_per_rubric_single_net`, Odoo `test_single_net_rule` |
| Règle d'or 13 (point non tranché = paramètre / option documentée) | CSV `source` (panier, solidarité, carburant : imposables par prudence ; logement D-14) ; `l10n_ga_tcs_deduct_cnamgs`, `l10n_ga_fnh_employee_share` datés | `test_housing_cash_allowance_fully_taxable` |
| Règle d'or 14 (dépendances) | `depends` = `hr_payroll`, `hr_work_entry_holidays`, `l10n_ga` | installation sur base neuve |
| D-16 (vocabulaire noyau = sélections Odoo) | `models/hr_salary_rule.py` | Odoo `test_selection_keys_match_core_vocabulary` |

Hors périmètre de 2.2 (sans objet) : règle d'or 11 (aucun nouveau modèle métier), 5, 6, 8.

## C3 — Chasse aux trous

| Contrôle | Résultat |
|---|---|
| `TODO|FIXME|XXX|HACK|NotImplementedError|pass$|...$` (module, `tools/`, `conftest.py`) | 0 |
| fichiers du manifeste absents / XML-CSV non déclarés | 0 / 0 (le catalogue CSV est une source de build, non chargé) |
| modèles sans ligne d'accès, multi-société sans règle | aucun nouveau modèle |
| champs de vue inexistants | aucune vue à cette étape |
| nombres littéraux dans les formules générées | 0 (test automatique) |
| `import odoo` dans `lib/ga_fiscal_core` | 0 (test AST + hook) |
| `_sql_constraints`, `attrs=`, `<tree` | 0 |
| méthodes publiques sans test | 0 (`param_codes`, `treatment`, générateurs `render/main/load_catalogue/read_generated/values_at`, contrainte) |
| libellés non traduisibles | 0 (`self.env._` pour le message utilisateur ; libellés de champs et de données exportés dans le `.pot`) |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur (ruff, ruff-format, odoo19-rules, pylint-odoo) |
| `make test-core` | outillage 55 passés ; noyau 368 passés, couverture **100 %** |
| `make test MODULE=l10n_ga_hr_payroll` | base neuve : code 0, **18 tests**, 0 ERROR/CRITICAL |
| `make upgrade MODULE=l10n_ga_hr_payroll` | code 0, 18 tests, 0 ERROR/CRITICAL |
| installation puis désinstallation | `uninstalled` ; restent 0 paramètre `l10n_ga_*`, 0 règle `GA_*`, 0 structure, 0 prestation `GA_*`, 0 colonne `l10n_ga_*` |

Avertissements non bloquants : « Missing `author` key in manifest » (question 1) ; avertissements de configuration du VPS (`db_host`, `http_interface`, `pdfminer`) sans lien avec le module.
Incident constaté : première tentative de désinstallation refusée (« Odoo is currently processing a scheduled action ») — une tâche planifiée du service `odoo19` tournait sur la base de test, conséquence directe de D-04 non appliqué. Réussie à la tentative suivante.

## C5 — Recette chiffrée

Le noyau n'a pas changé (parité oracle, 04 §8, jeux 06 §3 : verts). Recette ajoutée pour cette étape, **avec les données générées** (`tools/tests/test_recette_f16_generated_data.py`) : paramètres lus dans `hr_rule_parameters_data.xml` au 30/09/2026 et traitement des lignes lu dans le catalogue (`BASIC`, `GA_TRANSP`, `GA_RESP`) :

| Montant | Attendu (F16) | Obtenu | Écart |
|---|---|---|---|
| assiette sociale / imposable | 555 000 / 450 000 | 555 000 / 450 000 | 0 |
| CNSS / CNAMGS salariales | 27 750 / 11 100 | 27 750 / 11 100 | 0 |
| TCS / IRPP | 13 058 / 23 195 | 13 058 / 23 195 | 0 |
| **net** | **514 897** | **514 897** | 0 |
| CNSS patronale / CNAMGS / FNH / CFP | 99 900 / 22 755 / 16 650 / 2 775 | idem | 0 |
| variante tout imposable, net | 486 617 | 486 617 | 0 |

Parité paramètres : `FiscalParams` reconstruits depuis le XML = `load_from_yaml` aux 31/12/2025, 01/01/2026, 16/07/2026, 17/07/2026 (égalité exacte) ; côté Odoo, `params_from_values` sur les valeurs installées donne CNSS 5 %, FNH 3 %, barème ouvert.

## C6 — Complétion effectuée pendant le protocole

- Collecte pytest cassée par le nouvel `__init__.py` de l'addon (import `odoo`) → `conftest.py` racine (`pytest_collect_directory`) et suppression de `lib/tests/__init__.py`.
- Lecture du XML généré dupliquée dans les tests → `read_generated` / `values_at` dans le générateur, réutilisés par la recette.
- pylint-odoo : `self.env._`, clé de manifeste superflue ; ruff : exceptions `F401` (`__init__.py` Odoo) et `B018` (manifeste).

## Bloquants

Aucun.

## Questions pour Alex (non bloquantes)

1. **Auteur du manifeste** : Odoo avertit à chaque installation (« Missing `author` key »). Quel nom mettre (toi, ta société) ? En attendant, la clé est absente.
2. **D-04** (`db_name`, `dbfilter`, `list_db` dans `odoo.conf`) : toujours non appliqué ; l'interférence des tâches planifiées du service sur les bases de test est maintenant **observée** (désinstallation refusée une fois). À appliquer avant l'étape 2.3, qui calculera des bulletins dans les tests.

## Dette technique acceptée

| Élément | Justification | Résorption |
|---|---|---|
| `GA_ANC`, `GA_HS`, `GA_CONGE` lus sur entrée saisie | le calcul par convention (ancienneté, taux HS, allocation 1/12) est le périmètre de 2.4 | étape 2.4 (le `source` du catalogue le mentionne) |
| `GA_AN_*` lus sur entrée saisie | la valorisation art. 93 passe par l'adaptateur du noyau | étape 2.3 |
| Règles fiscales (`GA_CNSS_SAL`, `GA_IRPP`…) absentes de la structure | elles appellent `payslip._l10n_ga_compute`, créé en 2.3 | étape 2.3 |
| Bloc « Fiscalité Gabon » du formulaire de règle absent | vue prévue en 2.3 (D-16) | étape 2.3 |
| `security/l10n_ga_hr_payroll_security.xml` sans règle | aucun nouveau modèle métier à cette étape | étapes 2.4 à 2.6 |
| Prestations HS sans taux ni `is_extra_hours` | point 09-11 : aucune valeur par défaut ; traitement par la convention | étape 2.4 (risque de paiement par `amount_rate` à vérifier) |
