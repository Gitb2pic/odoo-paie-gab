# Complétude — `l10n_ga_hr_payroll`, étape 2.4 (conventions, grilles, heures supplémentaires, absences)

Date : 24/09/2026 — plan : `docs/plans/2.4.md` (« go avec tes recommandations » ; P1 à P6 → D-23 à D-28).

## Score

**18 / 18 éléments attendus présents et testés = 100 %.** Aucun bloquant.

## C1 — Inventaire attendu / réel

| # | Élément attendu (prompt 2.4, RG04, RG18, F4, F5) | État | Emplacement |
|---|---|---|---|
| 1 | `l10n_ga.collective.agreement` (règle d'ancienneté : début, taux de début, pas, plafond ; base) | présent | `models/l10n_ga_collective_agreement.py` |
| 2 | `l10n_ga.overtime.rate` (tranches, période jour/nuit/dimanche/férié, taux, **aucune valeur par défaut**) | présent | `models/l10n_ga_overtime_rate.py` |
| 3 | `l10n_ga.agreement.grade` (catégorie, échelon, minimum, taux horaire, date d'effet) | présent | `models/l10n_ga_agreement_grade.py` |
| 4 | `hr.version.l10n_ga_agreement_id`, `l10n_ga_grade_id` (+ date d'ancienneté) | présent | `models/hr_version.py`, related sur `hr.employee` |
| 5 | convention d'exemple marquée comme exemple | présent | `data/l10n_ga_collective_agreement_example.xml` (noupdate, « EXEMPLE », `is_example`, sans taux HS) |
| 6 | `GA_ANC` selon la convention | présent | `_l10n_ga_seniority_bonus`, noyau `labour.seniority_rate` |
| 7 | heures supplémentaires par la table de la convention | présent | `GA_HS_J/N/DIM/FER`, `_l10n_ga_overtime`, noyau `labour.overtime_amount` |
| 8 | `BASIC` proratisé par les prestations, jamais par une retenue (B2) | présent | standard `paid_amount` ; prestations HS hors base (`is_extra_hours`, `amount_rate` 0) |
| 9 | `GA_CONGE` (allocation de congé) | présent | `_l10n_ga_leave_allowance`, noyau `labour.leave_allowance`, 6 paramètres datés (D-23) |
| 10 | lien types de congés ↔ types de prestations | présent | `data/hr_leave_type_data.xml` (2.2), testé |
| 11 | congé payé hors salaire de base, payé par l'allocation (F4) | présent | `GA_CP` mode `allowance` + `unpaid_structure_ids` |
| 12 | maternité / AT subrogées | présent | `res.company.l10n_ga_cnss_subrogation`, `hr_payslip_worked_days._compute_is_paid` (D-26) |
| 13 | contrôle bloquant salaire < minimum de grille | présent | contrainte `hr.version._check_l10n_ga_grade` + anomalie native `danger` du bulletin + refus au figement |
| 14 | vues et menus | présent | `views/l10n_ga_collective_agreement_views.xml` (Paie → Configuration → Salaire), fiche salarié, société |
| 15 | sécurité : accès et règles multi-société | présent | `security/ir.model.access.csv` (6 + 2 lignes RH en lecture), `security/l10n_ga_hr_payroll_security.xml` (3 règles) |
| 16 | `test_absences.py` | présent | 5 tests (12 absences en sous-tests) |
| 17 | tests ancienneté (début, pas, plafond) et grille (salaire sous le minimum refusé) | présent | `tests/test_agreement.py` (14 tests) |
| 18 | noyau pur testé | présent | `lib/tests/test_labour.py` (29 cas) |

## C2 — Traçabilité exigence → code → test

| Exigence | Code | Test |
|---|---|---|
| RG04 (convention : taux HS et ancienneté) | `l10n_ga.collective.agreement`, `_overtime_tranches`, `_seniority_rate_at` | `test_seniority_on_grade_minimum`, `test_overtime_by_tranche` |
| RG18 (grade, minimum à la date, bloquant) | `_check_l10n_ga_grade`, `_l10n_ga_blocking_issues`, `_get_errors_by_slip`, `_l10n_ga_freeze` | `test_wage_below_grade_minimum_refused`, `test_grade_must_belong_to_agreement`, `test_grade_revalued_blocks_payslip`, `test_grade_unique_per_date` |
| RG06 (valeur datée de la grille) | `l10n_ga.agreement.grade._applicable` | `test_grade_revalued_blocks_payslip` (295 400 au 31/08, 400 000 au 30/09) |
| F4 (12 absences) | données prestations / congés, `_compute_is_paid` | `test_each_absence_effect_on_basic_and_leave_allowance`, `test_maternity_and_work_accident_without_subrogation`, `test_leave_types_linked_to_work_entry_types` |
| F5 (grille, ancienneté de la convention) | modèles, `GA_ANC` | `test_seniority_cap_and_wage_base`, `test_no_seniority_before_start`, `test_seniority_defaults_to_first_contract`, `test_invalid_seniority_rule` |
| B2 (pas de retenue pour absence) | `BASIC` = `paid_amount` | assertion « aucun gain négatif » pour chaque absence |
| Point 09-11 (aucun taux HS par défaut) | `overtime_amount` lève sans tranche ; convention d'exemple sans taux | `test_overtime_without_rate_blocks`, `test_overtime_hours_not_covered_rejected`, `test_example_agreement_marked_and_without_overtime_rates` |
| D-23 (constantes des congés datées) | YAML `conges`, `param_codes` | `test_every_parameter_installed_for_gabon`, générateur `--check` |
| D-24 (tranches mensuelles) | `l10n_ga.overtime.rate` | `test_overtime_by_tranche`, `test_overlapping_tranches_refused` |
| D-25 (base de l'ancienneté) | `seniority_base` | `test_seniority_cap_and_wage_base` |
| D-26 (subrogation) | `l10n_ga_cnss_subrogation` | `test_maternity_and_work_accident_without_subrogation` |
| D-27 (exemple) | données noupdate | `test_example_agreement_marked_and_without_overtime_rates` |
| D-28 (GA_ANC, GA_CONGE calculés) | catalogue `core`, types d'entrée supprimés | `test_labour_rubrics_computed`, `test_input_types` |
| Allocation de congé (1/12, 5/48, plus favorable) | `leave_allowance`, `_l10n_ga_leave_reference_pay`, `_l10n_ga_is_minor` | `test_leave_allowance_twelfth_more_favourable` (53 667), `test_leave_allowance_minor`, maintien (40 000) |
| Règle d'or 1 | taux de convention, paramètres datés ; `MONTHS_PER_YEAR` = constante de calendrier | `test_no_numeric_literal_in_formulas` |
| Règle d'or 11 (multi-société) | `company_id` requis / related stocké, `check_company`, règles | `test_multi_company_rule` |
| Bulletin figé : gains recalculés au contrôle | `_l10n_ga_expected` (gain proratisé) | tests 2.3 de figement (verts) + `test_grade_revalued_blocks_payslip` |

## C3 — Chasse aux trous

| Contrôle | Résultat |
|---|---|
| `TODO|FIXME|XXX|HACK|NotImplementedError|pass$|...$` | 0 |
| fichiers du manifeste absents / non déclarés | 0 / 0 (`catalogue_rubriques_ga.csv` = source de build) |
| modèles sans accès, sans règle multi-société | 0 (3 modèles : utilisateur paie en lecture, responsable paie complet, RH en lecture pour convention et grade ; 3 règles `company_id in company_ids`) |
| champs de vue inexistants | 0 (installation) |
| nombres littéraux | `MONTHS_PER_YEAR = 12` (calendrier, documenté) ; aucun taux |
| `import odoo` dans le noyau | 0 |
| syntaxe pré-19 | 0 |
| libellés non traduisibles | 0 (`self.env._` sur `UserError` / `ValidationError`) |

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | outillage 64 passés ; noyau 398 passés, couverture **100 %** |
| `make test MODULE=l10n_ga_hr_payroll` | base neuve : code 0, **69 tests**, 0 ERROR/CRITICAL |
| `make upgrade MODULE=l10n_ga_hr_payroll` | code 0, 69 tests, 0 ERROR/CRITICAL |
| installation sur base avec salarié existant, puis désinstallation | parts 3,0 / nationalité 2 ; `uninstalled`, 0 colonne, 0 table `l10n_ga_*`, 0 paramètre, 0 règle |
| `make i18n` | code 0 |

Corrigé pendant C4 : **unicité des grades** non garantie avec un échelon vide (NULL ≠ NULL en PostgreSQL) → `models.UniqueIndex` avec `COALESCE` ; prestations d'heures sup. de 2.2 comptées dans les heures de présence (`is_extra_hours` faux, `amount_rate` 1) → corrigées ; `dateutil` absent de l'environnement de lint → `completed_years` du noyau ; `no-member` de pylint retiré (faux positifs des modèles hérités selon le découpage des lots de pre-commit : la version 2.3 en produisait déjà 25 sur le fichier seul).

## C5 — Recette chiffrée

| Cas | Attendu | Obtenu | Écart |
|---|---|---|---|
| ancienneté 6 ans, grade C1 (295 400), tronc commun | 17 724 | 17 724 | 0 |
| idem plafonnée à 5 % / base salaire 350 000 | 14 770 / 21 000 | idem | 0 |
| 2 jours d'absence non payée, salaire 440 000 (176 h) | BASIC 400 000 | 400 000 | 0 |
| 2 jours de congé payé sans historique | BASIC 400 000 + GA_CONGE 40 000 (maintien) | idem | 0 |
| idem avec 6 440 000 de base congés sur 12 mois | GA_CONGE 53 667 (1/12 × 2,4 / 24) | 53 667 | 0 |
| maternité / AT : subrogation / sans | BASIC 440 000 / 400 000 | idem | 0 |
| 4 h sup. de jour, tranches 2 h à +10 % puis +25 % | 350 000 / 173,33 × (2,2 + 2,5) | idem | ≤ 1 |
| F16 et profils 2.3 | inchangés | verts | 0 |

## Bloquants

Aucun.

## Questions pour Alex (non bloquantes)

1. **Commits externes** : pendant les tests, un commit `25e35b1` (« convention collective, heures sup, absences », auteur `Gitb2pic`) a été créé et poussé avec le travail en cours, et les commits précédents de la session ont été réécrits (nouveaux identifiants). Rien n'est perdu : le seul correctif manquant (index des grades) est dans `553213a`, non poussé. Est-ce un outil de synchronisation automatique ? Faut-il que je pousse moi-même à la fin des étapes ?
2. **Démo** : `make demo MODULE=l10n_ga_hr_payroll` sur `odoo19` (redémarre le service) — sur ton accord.

## Dette technique acceptée

| Élément | Justification | Résorption |
|---|---|---|
| Tranches d'heures sup. mensuelles (pas hebdomadaires) | prestations mensuelles ; tranches saisies par le client (D-24) | si une convention exige le calcul hebdomadaire |
| Période de référence du congé = 12 mois glissants de bulletins Odoo | sans cumuls d'ouverture, le maintien protège le salarié | étape 2.6 (F12) |
| Acquisition des droits à congé (2 j/mois, mères, ancienneté) | relève des allocations `hr_holidays`, hors prompt | à décider |
| Créance CNSS de la subrogation | écriture comptable | étape 3 |
| Suspension de l'ancienneté par les absences | date d'ancienneté modifiable | sans objet |
