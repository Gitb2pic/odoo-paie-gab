# Sprint 0 — Vérifications du code Enterprise (points 🔒)

Lecture du 24/09/2026. `$ENTERPRISE_PATH` = `/home/ubuntu/odoo/enterprise` (commit `35b39159`), `$ODOO_PATH` = `/home/ubuntu/odoo/odoo` (commit `2e2acfd6`). Chemins ci-dessous relatifs à ces racines (préfixes `E/` et `C/`).

**Ce fichier remplace toute hypothèse 🔒 de `docs/architecture/`** (CLAUDE.md §2, priorité 1).

## Numérotation des points

Le prompt 01 annonce « 10 points du fichier 05 §7 », mais ce paragraphe n'en contient que **8** (`06` §6 dit aussi « 8 points »). Numérotation retenue (décision D-01 de `docs/decisions/ouvertes.md`) :

- 1 à 8 : fichier `05` §7 ;
- 9 : `hr.salary.attachment` accepte-t-il des gains (condition d'ADR-16, citée par le prompt) ;
- 10 : vue formulaire des règles salariales et groupes `hr_payroll` (🔒 restants de `05` §2.3 et `01` §6) ;
- 11 à 14 : ajoutés par le prompt 01.

## Synthèse

| # | Sujet | Résultat | Impact |
|---|---|---|---|
| 1 | Lien bulletin → version | `version_id` ✔, `contract_id` absent | aucun |
| 2 | Variables de `amount_python_compute`, `_rule_parameter` | `payslip` = vrai enregistrement ; `_rule_parameter` ✔ | aucun (précisions) |
| 3 | Validation de lot, états | `hr.payslip.run.action_validate` ✔ ; états bulletin **`draft/validated/paid/cancel`** (pas `done`) | **ajustement** (`04` §3, §11) |
| 4 | Comptes des règles, regroupement | `account_debit`/`account_credit` ✔ mais **`company_dependent`** ; regroupement par option société | **ajustement** (`05` §3) |
| 5 | Rapport générique réutilisable pour la DAS | aucun ; seul `hr.payroll.declaration.mixin` (attestations PDF par salarié) | aucun |
| 6 | Prêts / avances ; entrées créées hors bulletin | pas de modèle de prêt ; `hr.salary.attachment` = retenues à montant fixe ; `hr.payslip.input` exige un bulletin | **ajustement** (F1) |
| 7 | `l10n_account_withholding_tax` : multi-paiements, avoirs | retenue au paiement ; paiements partiels proratisés ; **pas de retenue sur paiements groupés non regroupés** ; avoirs gérés | ajustement (étape 5) |
| 8 | Schéma `hr_payroll_gb` chez le client | **non vérifiable** (ni base client ni module sur le VPS) | bloquant pour l'étape 6 seulement |
| 9 | `hr.salary.attachment` accepte des gains ? | **oui** (le signe est porté par la règle qui lit l'entrée) | **ADR-16** proposé |
| 10 | Vue formulaire des règles, groupes | `hr_payroll.hr_salary_rule_form` ; groupes `group_hr_payroll_user` / `_manager` ✔ | aucun |
| 11 | `hr.rule.parameter` | valeur = littéral Python (`safe_eval`) : nombre, liste, dict, tuple ; date = `date_to` ; code **unique global**, **pas de filtre société/pays** | ajustement mineur (générateur) |
| 12 | Ordre des règles ; règle courante | tri par `sequence` puis `id` ; **règle courante absente du localdict** ; code dupliqué = écrasement silencieux | **ajustement** (`l10n_ga_prorate`) |
| 13 | Méthodes de validation (F7, ADR-10) | `hr.payslip.action_payslip_done` (bulletin et lot) ; `action_payslip_paid` ; `write(state='paid')` | **ajustement** (`04` §11) |
| 14 | `l10n_account_withholding_tax` en 19.0 | **dans Community** (`C/addons`), dépend de `account` seul | aucun |

Découverte hors liste, qui touche ADR-18 : `hr.payslip` a en 19.0 un **mécanisme natif d'anomalies** (`issues`, `error_count`, `warning_count`) qui **bloque la validation** en cas d'erreur (voir point 13 et ADR-18).

---

## 1. Lien bulletin → version ; suppression de `contract_id`

**Réponse.** `hr.payslip.version_id` (Many2one `hr.version`, calculé, stocké, modifiable, indexé, domaine sur les dates de version). `contract_id` n'existe plus sur le bulletin : aucune occurrence dans `E/hr_payroll/models/hr_payslip.py`. Les seules traces du mot dans `hr_payroll/models` sont un nom de méthode historique (`_compute_contract_ids`, `hr_work_entry_export_mixin.py:207`) qui calcule en fait `version_ids`.

**Preuve.** `E/hr_payroll/models/hr_payslip.py:114`
```python
version_id = fields.Many2one('hr.version', string='Employee Record', precompute=True,
    tracking=True, compute='_compute_version_id', store=True, readonly=False, index=True, ...)
```
Les lignes portent aussi la version : `E/hr_payroll/models/hr_payslip.py:1236` (`'version_id': localdict['version'].id`), `hr.payslip.line._order = 'version_id, sequence, code'` (`E/hr_payroll/models/hr_payslip_line.py:11`).

**Impact.** Aucun : confirme `04` §2 (`self.version_id`) et `03` (`hr_payslip }o--|| hr_version : version_id`).

## 2. Variables de `amount_python_compute` ; `_rule_parameter`

**Réponse.** Le localdict est construit par `hr.payslip._get_localdict()` :

| Clé | Contenu |
|---|---|
| `payslip` | **l'enregistrement `hr.payslip` lui-même** (plus d'objet « Browsable ») → `payslip._l10n_ga_compute(...)`, `payslip._rule_parameter(...)` utilisables |
| `version`, `employee` | enregistrements `hr.version`, `hr.employee` |
| `categories` | `DefaultDictPayroll` (dict, défaut 0) indexé par code de catégorie : `categories['GROSS']` (pas d'accès par attribut) |
| `rules`, `result_rules` | dicts par code de règle (`total`, `amount`, `quantity`, `rate`, `ytd`) |
| `inputs` | `{code: hr.payslip.input}` (agrégateur si plusieurs entrées du même type) |
| `worked_days` | `{code: hr.payslip.worked_days}` |
| `property_inputs`, `same_type_input_lines` | entrées « propriétés » ; lignes multiples |
| outils | `float_round`, `float_compare`, `relativedelta`, `ceil`, `floor`, `UserError`, `date`, `datetime`, `defaultdict` |
| après chaque règle | `localdict[<code règle>] = total` |
| sortie | `result`, `result_qty`, `result_rate`, `result_name` |

**Preuve.** `E/hr_payroll/models/hr_payslip.py:1046-1057` (outils), `:1059-1092` (localdict, `'payslip': self` l.1078, `'version'` l.1084), `:25-29` (`DefaultDictPayroll`), `:973-978` (`_rule_parameter`), `E/hr_payroll/models/hr_salary_rule.py:191-192` (exécution `safe_eval(..., mode='exec')`, lecture de `result`, `result_qty`, `result_rate`).

**Impact.** Aucun. Précision pour l'étape 2.3 : `amount_python_compute` s'exécute sous `safe_eval` ; les appels passent par des méthodes de `payslip` (pas d'import possible dans la règle), ce qui convient au patron Adapter (`result = -payslip._l10n_ga_compute('irpp', categories)`).

## 3. Validation d'un lot ; états du bulletin

**Réponse.**
- Lot : `hr.payslip.run.action_validate()` → `slip_ids.filtered(state != 'cancel' and line_ids).action_payslip_done()`.
- Bulletin : bouton `hr.payslip.action_validate()` (calcule si besoin puis `action_payslip_done()`).
- États du bulletin : **`draft`, `validated`, `paid`, `cancel`** — il n'y a **plus d'état `done`** (le libellé affiché « Done » correspond à `validated`).
- États du lot (calculés depuis les bulletins) : `01_ready`, `02_close`, `03_paid`, `04_cancel`.
- Le standard lui-même filtre les cumuls sur `state in ('validated', 'paid')` (`_sum`, `_sum_category`, `_get_last_ytd_payslips`).

**Preuve.** `E/hr_payroll/models/hr_payslip.py:67-72` (états), `:643-645` (`action_validate`), `E/hr_payroll/models/hr_payslip_run.py:31-39` (états du lot), `:291-294` (`action_validate`), `E/hr_payroll/models/hr_payslip.py:987` (`hp.state in ('validated', 'paid')`).
```python
state = fields.Selection([('draft', 'Draft'), ('validated', 'Validated'), ('paid', 'Paid'), ('cancel', 'Canceled')], ...)
```

**Impact.** **Ajustement** : `04` §3 (`('slip_id.state', 'in', ('done', 'paid'))`) doit devenir `('validated', 'paid')`. Aucun code ne doit tester `'done'`. Le point d'accroche de l'Observer est traité au point 13.

## 4. Champs comptables des règles ; regroupement des écritures

**Réponse.**
- `hr.salary.rule.account_debit` / `account_credit` existent (Many2one `account.account`) mais sont **`company_dependent=True`** : une valeur par société, pas une colonne classique. Autres champs : `not_computed_in_net`, `debit_tag_ids`, `credit_tag_ids`, `split_move_lines`, `employee_move_line`, `analytic_distribution`.
- Journal : porté par la structure (`hr.payroll.structure.journal_id`) ; le bulletin le lit en related.
- Regroupement : option société `res.company.batch_payroll_move_lines`. Vraie → **une pièce par journal et par mois** pour tous les bulletins traités (y compris ceux du même lot), liée au lot (`hr.payslip.run.move_id`) ; fausse → une pièce par bulletin.
- Les pièces sont créées **après** `super().action_payslip_done()` par `_action_create_account_move()`.
- Le standard fournit un **hook de plan comptable** : `account.chart.template._configure_payroll_account_<code_modèle>(companies)` appelé après chargement du plan, qui affecte journal et comptes par société via `_configure_payroll_account(companies, country_code, account_codes, rules_mapping, default_account)`. Le plan gabonais a le code **`ga`** (et `ga_syscebnl`), parent `syscohada` (`C/addons/l10n_ga/models/template_ga.py:8-13`).

**Preuve.** `E/hr_payroll_account/models/hr_salary_rule.py:11-16`, `E/hr_payroll_account/models/res_company.py:10`, `E/hr_payroll_account/models/hr_payslip.py:43-52` et `:54-122`, `E/hr_payroll_account/models/account_chart_template.py:16-69` ; exemples : `E/l10n_ke_hr_payroll_account/models/account_chart_template.py:12`, `E/l10n_ma_hr_payroll_account/models/account_chart_template.py:12`.
```python
account_debit = fields.Many2one('account.account', 'Debit Account', company_dependent=True, ondelete='restrict', ...)
```

**Impact.** **Ajustement** de `05` §3 : `l10n_ga_hr_payroll_account` ne doit pas écrire `account_debit`/`account_credit` par données XML (valeur liée à une seule société, comptes créés par société à l'installation du plan). Il implémente `_configure_payroll_account_ga` (et `_ga_syscebnl`) avec `rules_mapping` = table règle → comptes `pcg_*`, plus une action de reconfiguration pour les sociétés déjà installées. À reprendre dans le plan de l'étape 3 (pas d'ADR : c'est le point d'extension standard).

## 5. Localisation « générique » ou rapport réutilisable pour la DAS

**Réponse.** Non. `hr_payroll` ne contient pas d'analyse de paie réutilisable pour une DAS : `report/` n'a que le registre de cotisations (`report.hr_payroll.contribution_register`) et l'analyse des prestations (`hr.work.entry.report`). Il existe un cadre abstrait `hr.payroll.declaration.mixin` + `hr.payroll.employee.declaration` : **attestations annuelles PDF par salarié** (année, lignes par salarié, génération PDF), utilisé par les localisations BE (281.10/281.45), CH, HK (IRD), KE, IN.

**Preuve.** `E/hr_payroll/models/hr_payroll_declaration_mixin.py:15-40`, `E/hr_payroll/models/hr_payroll_employee_declaration.py:15-28`, `E/hr_payroll/report/` (2 fichiers), utilisateurs : `E/l10n_be_hr_payroll/models/l10n_be_281_10.py`, `E/l10n_ke_hr_payroll/models/l10n_ke_tax_deduction_card.py`.

**Impact.** Aucun : le moteur `l10n_ga.declaration` (ADR-06/07) reste nécessaire (déclaration société, cases, Excel DGI, état figé). Piste pour plus tard (hors périmètre actuel) : le mixin pourrait produire des attestations individuelles de salaires ; à ne pas utiliser pour la DAS.

## 6. Prêts / avances dans `hr_payroll` 19 ; entrées créées hors bulletin

**Réponse.**
- **Pas de modèle de prêt.** Le seul point d'entrée est un hook vide `hr.payslip._get_salary_advance_balances()` (retourne `defaultdict(float)`), sans utilisateur dans `hr_payroll`. `account_loans` (Enterprise) gère des emprunts **comptables** (dépend de `account_asset`), pas des prêts au personnel.
- `hr.salary.attachment` (« Salary Adjustment ») : montant par bulletin (`monthly_amount > 0`), total, restant, durée `one/limited/unlimited`, dates, `record_payment()` appelé quand le bulletin passe à `paid`. **Pas d'échéancier daté, pas d'intérêts, pas de plafond d'encours, pas de remboursement anticipé ni de dérogation.**
- `hr.payslip.input.payslip_id` est **obligatoire** : une entrée ne peut pas exister « hors bulletin ». Les entrées d'un type `available_in_attachments` sont **supprimées puis recréées** par `_compute_input_line_ids` à chaque changement de salarié, version, structure ou dates ; les autres entrées (saisies ou créées par code) sont conservées, et `compute_sheet()` ne les supprime pas (il ne vide que `line_ids`).

**Preuve.** `E/hr_payroll/models/hr_payslip.py:184-185` (hook avance), `:285-312` (`_compute_input_line_ids`), `:478-492` (`write` → `_record_attachment_payment`), `E/hr_payroll/models/hr_salary_attachment.py:19-34` (contraintes), `:371-410` (`record_payment`), `E/hr_payroll/models/hr_payslip_input.py:13` (`payslip_id ... required=True`), `E/account_loans/__manifest__.py`.

**Impact.** **Ajustement** (pas d'ADR) : F1 garde son modèle `l10n_ga.employee.loan` + échéances (le standard ne couvre ni échéancier, ni plafond 40 %, ni anticipation). Contraintes pour l'étape 2.5 :
1. le type d'entrée `GA_LOAN` **ne doit pas** être `available_in_attachments` (sinon effacé et recalculé par le standard) ;
2. les entrées `GA_LOAN` sont créées **sur le bulletin brouillon** (à la génération du lot / au calcul), jamais à l'avance ;
3. l'échéance est soldée au passage `paid` du bulletin (même moment que le standard pour les saisies).

## 7. `l10n_account_withholding_tax` : multi-paiements et avoirs (base de l'ID18)

**Réponse.** Retenue calculée **au paiement** (assistant `account.payment.register`), pas sur la facture :
- taxe marquée `account.tax.is_withholding_tax_on_payment` ; lignes `account.payment.withholding.line` (héritent de l'abstrait `account.withholding.line` : `tax_id`, `base_amount`, `amount`, `source_*`, `original_*`, `comodel_percentage_paid_factor`, `name` = numéro de pièce de retenue) ;
- **paiement partiel / échéances** : base multipliée par `comodel_percentage_paid_factor` = montant payé / total (facteur « split » pour les échéances) ;
- **plusieurs factures** : la retenue n'est proposée **que si une seule écriture de paiement est créée** (`display_withholding = False` si `can_group_payments and not group_payment`, ou si l'assistant n'est pas éditable) → **paiement groupé de plusieurs factures non regroupé = pas de retenue** ;
- **avoirs** : sens de la taxe inversé (`is_refund` → `payment_type` inversé) ; test standard `test_tax_repartition_on_refund`.

**Preuve.** `C/addons/l10n_account_withholding_tax/wizards/account_payment_register.py:98-124` (affichage, multi-écritures, avoirs), `:130-153` (lignes par défaut depuis les factures), `C/addons/l10n_account_withholding_tax/wizards/account_payment_register_withholding_line.py:41-60` (facteur payé), `C/addons/l10n_account_withholding_tax/models/account_tax.py:13-24`, tests `C/addons/l10n_account_withholding_tax/tests/test_account_withholding_flows.py:514` (échéances), `:1072` (avoirs).

**Impact.** Ajustement à l'étape 5 (`l10n_ga_dgi_edi_account`) : le générateur ID18/ID27 lit `account.payment.withholding.line` (ou les écritures de retenue et leurs grilles), et un **contrôle** signale les factures fournisseurs soumises à RAS payées dans un paiement groupé sans retenue. Tests à prévoir : paiement partiel, deux échéances, avoir.

## 8. Schéma des tables `hr_payroll_gb` chez le client

**Réponse.** **Non vérifiable** au sprint 0 : le module `hr_payroll_gb` n'est ni dans l'`addons_path`, ni dans une base du VPS (seules `odoo19` et `postgres` existent), et aucun dump client n'est fourni.

**Impact.** Bloquant **uniquement pour l'étape 6** (module de reprise). Question à Alex : fournir un dump anonymisé (ou `pg_dump --schema-only` + quelques lignes) des tables `hr_payroll_gb` de la base client avant l'étape 6.

## 9. `hr.salary.attachment` accepte-t-il des gains ?

**Réponse.** **Oui.** Le modèle ne connaît ni gain ni retenue : il pousse une entrée de bulletin (`hr.payslip.input`) d'un type `available_in_attachments`, de montant positif (négatif si `is_refund`). C'est la **règle salariale** qui lit l'entrée qui fixe le signe et la catégorie. Un type d'entrée « indemnité de logement » lu par une règle de gain est donc accepté. La durée `unlimited` + `date_start`/`date_end` donne une **ligne datée** par salarié. Limites : montant fixe par bulletin (pas de prorata intégré), lien sur `employee_ids` (pas sur `hr.version`), message de contrainte orienté « retenue ».

**Preuve.** `E/hr_payroll/models/hr_salary_attachment.py:44-50` (type d'entrée), `:51-62` (durée), `:93-95` (`is_refund`), `:413` (`_get_active_amount`), `E/hr_payroll/models/hr_payslip.py:296-311` (création de l'entrée sur le bulletin selon les dates), `E/hr_payroll/models/hr_payslip_input_type.py:23` (`available_in_attachments`).

**Impact.** **ADR-16 proposé** (`docs/adr/ADR-16-indemnites-contractuelles-lignes-datees.md`) : indemnités contractuelles = `hr.salary.attachment` datés, prorata par la règle (point 12).

## 10. Vue formulaire des règles salariales ; groupes `hr_payroll`

**Réponse.** Vue `hr_payroll.hr_salary_rule_form` ; points d'insertion stables : `group[@name='main_details']`, `page[@name='general']`, `group[@name='general_conditions']`, `page[@name='display']`. `hr_payroll_account` l'étend déjà (`hr_payroll_account.hr_salary_rule_view_form`). Groupes : `hr_payroll.group_hr_payroll_user` (implique `hr.group_hr_user`), `hr_payroll.group_hr_payroll_manager` (implique le précédent et `hr.group_hr_manager`). Les montants de `hr.version` (`wage`, `contract_wage`, `hourly_wage`) sont déjà restreints à `hr_payroll.group_hr_payroll_user`.

**Preuve.** `E/hr_payroll/views/hr_salary_rule_views.xml:47` (vue), `:57` (`main_details`), `:70` (`general`), `:120` (`general_conditions`), `:160` (`display`), `E/hr_payroll_account/views/hr_salary_rule_views.xml:3-6`, `E/hr_payroll/security/hr_payroll_security.xml:11-23`, `E/hr_payroll/models/hr_version.py:28-29,46`.

**Impact.** Aucun : bloc « Fiscalité Gabon » ajouté dans une nouvelle `page` après `page[@name='general']` ; les champs montants Gabon sur `hr.version` prennent `groups="hr_payroll.group_hr_payroll_user"`.

## 11. `hr.rule.parameter` / `_rule_parameter(code)`

**Réponse.**
- Signature : `hr.payslip._rule_parameter(code, reference_date=False)` → `hr.rule.parameter._get_parameter_from_code(code, date, raise_if_not_found=True)` ; **date par défaut = `payslip.date_to`**.
- Valeur : `hr.rule.parameter.value.parameter_value` = **Text évalué par `safe_eval`** → tout littéral Python : nombre, chaîne, liste, tuple, dict (donc un barème `[(plafond, taux), ...]` ou un dict). Contrainte d'évaluabilité à l'écriture. Retour en `deepcopy`.
- Sélection : dernière valeur avec `date_from <= date` (`_order = 'date_from desc'`, `limit=1`) ; unicité `(rule_parameter_id, date_from)`.
- Cache `ormcache(code, date, allowed_company_ids)`, vidé à chaque création/écriture/suppression de valeur.
- `hr.rule.parameter.code` **unique pour toute la base** ; `country_id` n'est **pas** utilisé dans la recherche (ni société ni pays).
- Paramètre absent → `UserError` (« No rule parameter with code ... »).

**Preuve.** `E/hr_payroll/models/hr_payslip.py:973-978`, `E/hr_payroll/models/hr_rule_parameter.py:15-30` (valeur, unicité), `:32-39` (contrainte `safe_eval`), `:62-72` (`country_id`, `_unique_code`), `:74-95` (lecture, cache).
```python
def _rule_parameter(self, code, reference_date=False):
    ...
    return self.env['hr.rule.parameter']._get_parameter_from_code(code, self.date_to)
```

**Impact.** Ajustement mineur (étape 2.2) : préfixe `l10n_ga_` obligatoire (unicité globale) ; `tools/yaml_to_rule_parameters.py` écrit des littéraux Python (`repr`) et non du JSON ; `_l10n_ga_params()` lit tous les codes une fois par bulletin à `date_to` (rappel : la date de référence métier, par exemple la date de paiement pour le FNH au 17/07/2026, doit être passée explicitement en `reference_date` si elle diffère de `date_to` — point à trancher dans le plan 2.2).

## 12. Ordre de calcul ; règle courante dans `amount_python_compute`

**Réponse.**
- Ordre : `sorted(payslip.struct_id.rule_ids, key=sequence)` ; `rule_ids` suit `hr.salary.rule._order = 'sequence, id'` → à `sequence` égale, ordre de création.
- Après chaque règle : `localdict[code] = total`, `result_rules[code]`, et ajout à `categories` (catégorie **et** parents, `_sum_salary_rule_category`).
- **La règle courante n'est pas dans le localdict** (`_compute_rule` n'ajoute que `localdict['localdict']`).
- Deux règles de même code dans une structure : la seconde **écrase** la première dans `result` (une seule ligne), mais les deux montants s'ajoutent aux catégories → c'est le mécanisme du défaut B1 (`NET` en double).

**Preuve.** `E/hr_payroll/models/hr_payslip.py:1174` (tri), `:1217-1244` (calcul, écrasement `result[rule.code]`), `E/hr_payroll/models/hr_salary_rule.py:16` (`_order`), `:159-194` (`_compute_rule`), `E/hr_payroll/models/hr_salary_rule_category.py:36-41`.

**Impact.** **Ajustement** (étape 2.3/2.5) : pour `l10n_ga_prorate`, surcharger `hr.salary.rule._compute_rule(localdict)` dans `l10n_ga_hr_payroll` pour exposer la règle courante (`localdict['l10n_ga_rule'] = self`) avant `super()`. Le test `test_rule_codes_unique.py` prévu (`06` §1) est indispensable (unicité des codes par structure, `NET` unique).

## 13. Méthode appelée à la validation d'un bulletin et d'un lot

**Réponse.**
- **Bulletin** : `hr.payslip.action_payslip_done()` — refuse les bulletins annulés ou avec `error_count`, écrit `state='validated'` et `done_date`, valide les prestations. Appelée par le bouton `action_validate()` **et** par le lot. `hr_payroll_account` la surcharge (création des pièces après `super()`).
- **Lot** : `hr.payslip.run.action_validate()` → délègue à `action_payslip_done()` des bulletins.
- **Paiement** : `hr.payslip.action_payslip_paid()` (état `paid`, `paid_date = today`) ; le standard réagit aussi dans `write()` quand `state` devient `paid`.
- **Anomalies natives** : `issues` (Json), `error_count`, `warning_count` stockés, calculés par `_get_errors_by_slip()` / `_get_warnings_by_slip()` sur `_issues_dependencies()` ; `error_count > 0` **bloque** `action_payslip_done` et `action_payslip_paid`. Le lot expose `payslips_with_issues`, `has_error`, `action_review_issues`. `hr_payroll_holidays` étend déjà `_get_errors_by_slip`.

**Preuve.** `E/hr_payroll/models/hr_payslip.py:607-641`, `:643-645`, `:654-665`, `:478-492`, `:150-152` (champs d'anomalies), `:1346-1440` (dépendances, erreurs, avertissements), `:1443-1456` (`_compute_issues`), `E/hr_payroll/models/hr_payslip_run.py:55-56`, `:231-239`, `:291-294`, `:331-344`, `E/hr_payroll_account/models/hr_payslip.py:43-52`, `E/hr_payroll_holidays/models/hr_payslip.py:17`.

**Impact.** **Ajustement** de `04` §11 et des diagrammes de séquence `02` :
- F7/F16 (bulletin figé) : surcharge de `hr.payslip.action_payslip_done()` qui stocke les valeurs figées **avant** `super()` (état encore `draft`, lignes calculées) ;
- ADR-10 (Observer) : s'accrocher à `hr.payslip.action_payslip_done()` plutôt qu'à `hr.payslip.run.action_validate()`, sinon un bulletin validé seul (hors lot, ou rectificatif) n'est pas vu ; pour l'ID10 basée sur la date de paiement, s'accrocher aussi à `action_payslip_paid()`.
- F8 : voir ADR-18.

## 14. `l10n_account_withholding_tax` en 19.0

**Réponse.** Présent **dans Community** : `C/addons/l10n_account_withholding_tax` (+ `l10n_account_withholding_tax_pos`), absent d'Enterprise. Manifeste : « Withholding Tax on Payment », `depends: ['account']`. Modèle de données : `account.tax` (+ `is_withholding_tax_on_payment`, `withholding_sequence_id`), `account.withholding.line` (abstrait), `account.payment.withholding.line` (`payment_id`), `account.payment.register.withholding.line` (assistant), `account.payment` (+ `should_withhold_tax`, `withholding_line_ids`, `display_withholding`), `res.company` / `res.config.settings` (+ `withholding_tax_base_account_id`), `product.template` (taxe de retenue par défaut).

**Preuve.** `C/addons/l10n_account_withholding_tax/__manifest__.py:3-7`, `models/account_tax.py:13-24`, `models/account_withholding_line.py:10-115`, `models/account_payment_withholding_line.py:5-18`, `models/account_payment.py:12-29`, `models/res_company.py:12`.

**Impact.** Aucun (dépendance Community, disponible partout) ; le détail du comportement est au point 7.
