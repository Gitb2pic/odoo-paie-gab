# Complétude — `l10n_ga_hr_payroll`, étape 2.3 (modèles, adaptateur et règles liées au noyau)

Date : 24/09/2026 — plan : `docs/plans/2.3.md` (« go avec D-04 » reçu ; P1 à P5 → décisions D-18 à D-22).

## Score

**22 / 22 éléments attendus présents et testés = 100 %.** Aucun bloquant de développement. Une action d'exploitation reste à Alex (D-04, refusée à Claude par les permissions). Un élément du prompt est reporté par le plan (`l10n_ga_rounding_carry`, F2 → étape 2.6), hors score.

## C1 — Inventaire attendu / réel

| # | Élément attendu (prompt 2.3, `05` §2.2-2.4, `04` §2-3, `08` F7/F16) | État | Emplacement |
|---|---|---|---|
| 1 | `hr.version` : enfants infirmes, demi-part | présent | `models/hr_version.py` |
| 2 | `l10n_ga_tax_parts` calculé stocké, parts forcées + motif | présent | idem (`_compute_l10n_ga_tax_parts`, `_check_l10n_ga_tax_parts`) |
| 3 | n° CNAMGS, NIF, code nationalité calculé (1-4) | présent | idem + `data/res_country_group_data.xml` (D-20) |
| 4 | codes emploi / niveau, trajets, véhicule de fonction, mode de paiement | présent | idem |
| 5 | avantages en nature fournis (D-18) | présent | idem (`l10n_ga_benefit_*`) |
| 6 | exposition sur `hr.employee` sans champ stocké (ADR-05) | présent | `models/hr_employee.py` (related `inherited=True`) |
| 7 | `res.company` : NIF, n° CNSS / CNAMGS, centre des impôts, segment, option CFP (déclaration + assiette), arrondi espèces (défaut lu dans le paramètre), plafond d'encours | présent | `models/res_company.py` ; part FNH = paramètre daté (D-19) |
| 8 | `hr.salary.rule` : bases sociale/fiscale, groupes, prorata, base congés, base rupture, colonnes DAS | présent | `models/hr_salary_rule.py` (2.2) + `l10n_ga_core_value`, `_compute_rule` (D-21) |
| 9 | `_l10n_ga_params()` | présent | `models/hr_payslip.py` → `res.company._l10n_ga_fiscal_params` (table `param_codes`) |
| 10 | `_l10n_ga_facts()` | présent | idem |
| 11 | `_l10n_ga_compute(code, categories, result_rules)` + cache du `PayResult` | présent | idem (`cr.cache`, clé = `PayslipFacts`) |
| 12 | `_l10n_ga_paid_ratio()`, `_l10n_ga_days_worked()` | présent | idem |
| 13 | cumuls annuels `_l10n_ga_ytd` | présent | idem (bulletins `validated`/`paid` de l'année civile) |
| 14 | `l10n_ga_payment_date` | présent | idem |
| 15 | champs figés F7 (parts, situation, plafonds, bases, cumuls `l10n_ga_ytd_*`) à la validation | présent | idem, `action_payslip_done` avant `super()` (D-22) |
| 16 | `hr.payslip.line` : `l10n_ga_social_excluded`, `l10n_ga_tax_exempt` figés (F16) | présent | `models/hr_payslip_line.py`, `_l10n_ga_freeze_lines` |
| 17 | règles fiscales en une ligne | présent | 12 rubriques `core` + 4 avantages en nature (catalogue, générateur) |
| 18 | vue fiche salarié (`hr_family_group`, `payroll_information`) | présent | `views/hr_employee_views.xml` |
| 19 | vue société (onglet « Gabon — Paie et fiscalité ») | présent | `views/res_company_views.xml` |
| 20 | vue règle salariale (« Fiscalité Gabon ») | présent | `views/hr_salary_rule_views.xml` ; + onglet « Gabon » du bulletin `views/hr_payslip_views.xml` |
| 21 | `test_tax_parts.py` | présent | 6 tests |
| 22 | `test_payslip_ga.py` (profils, versions, dates, parité, figé, F16) | présent | 18 tests (+ `common.py`, `test_hr_version_ga.py` 7 tests) |

Reporté par le plan (hors score) : `l10n_ga_rounding_carry` et les règles `GA_ROUND_PREV` / `GA_ROUND` / `GA_NET_PAY` → étape 2.6 (arrondi espèces F2).

## C2 — Traçabilité exigence → code → test

| Exigence | Code | Test |
|---|---|---|
| RG03 (parts, forçage 1 à 6,5 motivé) | `hr_version.py` → `ga_fiscal_core.tax_parts` | `test_parts_by_family_situation`, `test_disabled_children_and_extra_half_part`, `test_forced_parts_with_reason`, `test_forced_parts_rejected` |
| RG06 / D-06 (paramètre daté à `date_to`) | `_l10n_ga_params` | `test_dated_parameters_december_january_july` (CNSS 2,5 % → 5 %, FNH 2 % → 3 %) |
| Patron 2 (adaptateur) | `_l10n_ga_facts`, `_l10n_ga_gain_lines` | parité noyau (`assertCoreParity`) dans 10 tests |
| Patron 3 (Parameter Object) | `res.company._l10n_ga_fiscal_params` | `test_company_fiscal_params_with_options` |
| F7 (bulletin figé) | `_l10n_ga_freeze`, champs figés | `test_f16_frozen_per_line_and_per_slip`, `test_frozen_values_survive_parameter_change` |
| F16 (590 000 → 514 897, par ligne) | règles `core`, `_l10n_ga_freeze_lines` | `test_f16_net_514897_in_odoo`, `test_f16_frozen_per_line_and_per_slip` |
| F14 (seuil IRPP) | via `FiscalParams.irpp_min_withholding` | noyau (2.1) + paramètres installés (2.2) |
| ADR-05 (données sur la version) | `hr_version.py`, `hr_employee.py` | `test_employee_has_no_stored_ga_field` |
| ADR-17 (exonération par ligne, plafond par groupe) | `treatment.social_group/tax_group` dans l'adaptateur | F16 par ligne, `test_thirteenth_month_beyond_4m_cumulative` |
| Sprint 0 point 12 / D-21 (proratisation) | `hr.salary.rule._compute_rule` | `test_hired_on_the_15th_prorated` |
| Sprint 0 point 13 / D-22 (figer avant `super()`) | `action_payslip_done` | `test_frozen_values_survive_parameter_change`, `test_foreign_structure_not_frozen` |
| D-18 (avantages en nature par le noyau) | `benefit:<nature>`, `benefit_code` | `test_benefits_in_kind_valued_by_core`, `test_benefit_code_names_the_core_line`, `test_input_types` |
| D-19 (FNH salarial = paramètre daté) | règle `GA_FNH_SAL` | `test_f16_net_514897_in_odoo` (ligne absente à 0 %) |
| D-20 (nationalité par groupes de pays en données) | `res_country_group_data.xml` | `test_nationality_code_from_country`, `test_country_groups_are_data` |
| Régularisation IRPP (décembre ou départ) | `_l10n_ga_regularize` | `test_departure_with_irpp_regularisation`, `test_dated_parameters_december_january_july` |
| Cumuls annuels (année civile) | `_l10n_ga_ytd` | `test_ytd_limited_to_the_civil_year`, `test_thirteenth_month_beyond_4m_cumulative` |
| Cache (un calcul noyau par bulletin) | `_l10n_ga_result` | `test_core_computed_once_per_payslip` |
| Règle d'or 1 (aucun taux en dur) | formules générées sans nombre ; arrondi espèces par défaut lu dans le paramètre | `test_no_numeric_literal_in_formulas`, `test_company_cash_rounding_default_from_parameter` |
| Règle d'or 3 (NET unique) | catalogue | `test_single_net_rule`, `test_one_rule_per_rubric_single_net` |
| Règle d'or 5 | idem ADR-05 | idem |
| Règle d'or 8 (figé) | idem F7 | idem |
| Règle d'or 9 (arrondi au franc par ligne) | noyau ; `float_round` dans la proratisation | `test_hired_on_the_15th_prorated` |
| Règle d'or 13 (point 09 = option ou paramètre) | `l10n_ga_cfp_base` (D-10), FNH salarial (09-2), TCS/CNAMGS (09-3) | `test_company_fiscal_params_with_options` |
| Installation sur base existante | `_post_init_hook` | `test_post_init_hook_recomputes_existing_versions` + essai réel (C4) |

## C3 — Chasse aux trous

| Contrôle | Résultat |
|---|---|
| `TODO|FIXME|XXX|HACK|NotImplementedError|pass$|...$` | 0 (un `'XXX'` = valeur de catégorie invalide volontaire dans un test du générateur) |
| fichiers du manifeste absents / XML-CSV non déclarés | 0 / 0 (`catalogue_rubriques_ga.csv` = source de build) |
| modèles sans ligne d'accès, multi-société sans règle | aucun nouveau modèle ; bulletins lisibles par `group_hr_payroll_user` seulement (`E/hr_payroll/security/ir.model.access.csv:7`) |
| champs de vue inexistants | 0 (vues chargées à l'installation, qui échouerait sinon) |
| nombres littéraux (formules, noyau, modèles) | 0 hors aides et commentaires ; formules : test automatique (motif corrigé pour ne pas signaler `l10n`) |
| `import odoo` dans `lib/ga_fiscal_core` | 0 |
| `_sql_constraints`, `attrs=`, `<tree` | 0 |
| méthodes sans test | 0 (`action_payslip_done`, `_post_init_hook`, `_l10n_ga_*` de l'adaptateur, `_compute_rule`, `_l10n_ga_sign` via la parité) |
| libellés non traduisibles | 0 (`self.env._` pour `UserError` / `ValidationError`) ; `ValueError` de `_l10n_ga_value` = erreur de configuration technique |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur (2 `pylint: disable=no-member` ciblés : modèle Enterprise hors chemin d'analyse) |
| `make test-core` | outillage 63 passés ; noyau 369 passés, couverture **100 %** |
| `make test MODULE=l10n_ga_hr_payroll` | base neuve : code 0, **50 tests**, 0 ERROR/CRITICAL |
| `make upgrade MODULE=l10n_ga_hr_payroll` | code 0, 50 tests, 0 ERROR/CRITICAL |
| installation sur base **avec un salarié existant** puis désinstallation | parts 3,0 et nationalité 2 calculées par le `post_init_hook` ; `uninstalled`, 0 colonne `l10n_ga_*`, 0 paramètre, 0 règle `GA_*`, 0 groupe de pays |
| `make i18n` | `.pot` et `fr.po` régénérés |

Avertissements restants : configuration du VPS (`db_host`, `db_port`, `db_password`, `http_interface`, `pdfminer`), sans lien avec le module. Premier essai d'installation sur base existante coupé par la limite de 10 minutes de l'outil (installation complète de la comptabilité `l10n_ga`) ; relancé en arrière-plan : réussi.

Corrigé pendant C4 : xml_id des types d'entrée dans la fabrique de tests ; test 2.2 des types d'entrée mis à jour (D-18) ; **régularisation IRPP négative** (remboursement) comparée en valeur absolue → comparaison signée (`hr.salary.rule._l10n_ga_sign`).

## C5 — Recette chiffrée

| Cas | Attendu | Obtenu dans Odoo | Écart |
|---|---|---|---|
| F16 : brut / assiette sociale / imposable | 590 000 / 555 000 / 450 000 | idem (champs figés) | 0 |
| F16 : CNSS / CNAMGS / TCS / IRPP salariaux | 27 750 / 11 100 / 13 058 / 23 195 | idem (lignes) | 0 |
| F16 : **net** | **514 897** | **514 897** | 0 |
| F16 : CNSS patronale / CNAMGS / FNH / CFP | 99 900 / 22 755 / 16 650 / 2 775 | idem | 0 |
| F16 par ligne (exclu social, exonéré) | transport 35 000 / 35 000 ; responsabilité 0 / 105 000 | idem | 0 |
| Plafond CNSS (2 000 000, 2026) | CNSS 75 000, CNAMGS 40 000 | idem | 0 |
| CNSS salariale 12/2025 → 01/2026 | 25 000 → 50 000 | idem | 0 |
| FNH 01/2026 → 07/2026 | 20 000 → 30 000 | idem | 0 |
| 13e mois : 3 000 000 puis 2 000 000 | exonéré 3 000 000 puis 1 000 000 (cumul 4 000 000) | idem | 0 |
| profils 06 §3 (sous le seuil TCS, cadre au plafond de l'abattement, entré le 15, départ avec régularisation, changement d'enfants, avantages en nature) | noyau (parité ligne à ligne) | écart ≤ 1 FCFA sur chaque règle, brut et net | ≤ 1 |

Chaîne de confiance : Odoo = noyau (parité ci-dessus) ; noyau = calculateur de référence et exemples `04` §8 (tests 2.1, verts) ; paramètres installés = YAML (tests 2.2, verts). Le virtualenv Odoo n'a pas `yaml` : les tests Odoo lisent les paramètres installés, pas le YAML.

## Bloquants

Aucun bloquant de développement.

## Questions et actions pour Alex

1. **D-04 à appliquer** (refusé à Claude par les permissions malgré ton « go ») :
   `cp /home/ubuntu/odoo/odoo/debian/odoo.conf /home/ubuntu/odoo/odoo.conf.bak-20260924 && printf 'db_name = odoo19\ndbfilter = ^odoo19$\nlist_db = False\n' >> /home/ubuntu/odoo/odoo/debian/odoo.conf && sudo systemctl restart odoo19`
2. **Démo** : `make demo MODULE=l10n_ga_hr_payroll` sur `odoo19` (redémarre le service) — sur ton accord.

## Dette technique acceptée

| Élément | Justification | Résorption |
|---|---|---|
| Régularisation IRPP sans cumuls d'ouverture | un salarié repris en cours d'année n'a que ses bulletins Odoo dans le cumul : en décembre, la régularisation peut rembourser à tort | étape 2.6 (F12, `l10n_ga.ytd.opening` ajouté à `_l10n_ga_ytd`) ; contrôle F8 à prévoir |
| Arrondi espèces (`l10n_ga_rounding_carry`, `GA_ROUND*`) | périmètre F2 de l'étape 2.6 | étape 2.6 |
| `GA_ANC`, `GA_HS`, `GA_CONGE` saisis | calcul par convention | étape 2.4 |
| Parts de la version calculées à `date_version` | indicatives ; le bulletin recalcule à `date_to` et fige `l10n_ga_tax_parts_used` | sans objet |
| Plusieurs bulletins sur un même mois (changement de version en cours de mois) | chaque bulletin calculé séparément, cumuls sur les seuls bulletins validés | régularisation annuelle |
