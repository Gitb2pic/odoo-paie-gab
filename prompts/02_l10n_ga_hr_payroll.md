# Prompt 02 — Module `l10n_ga_hr_payroll` (7 étapes)

> Une étape = une session (`/clear` entre deux). Colle l'**en-tête commun** + le bloc de l'étape.

---

## En-tête commun (à coller à chaque étape)

Tu développes le module `l10n_ga_hr_payroll` (dépend de `hr_payroll` 🔒 et `l10n_ga`). Relis `CLAUDE.md`, `docs/PROGRESS.md`, `docs/sprint0_verifications_enterprise.md` et les ADR acceptés. Architecture de référence : `docs/architecture/05_integration_odoo.md` §2, `06` §1 (arborescence), `04` (patrons 1, 2, 3, 12, 13, 15, 16), `03` (RG02-RG08, RG18-RG30), `08` (F1-F8, F12-F16). Tu fais **uniquement l'étape ci-dessous**, tu présentes ton plan dans `docs/plans/2.X.md`, tu attends mon « go », puis tu codes en TDD et tu termines par le protocole de complétude (`CLAUDE.md` §7).

---

## Étape 2.1 — Noyau fiscal pur `lib/ga_fiscal_core`

**Lire d'abord** : base de connaissance `03` (CNSS/CNAMGS), `04` (IRPP, TCS, FNH, CFP — §7 algorithme, §8 exemples), `05` (rubriques, avantages en nature, exonérations art. 91 / 91 bis), `09` (hypothèses), `parametres_fiscaux_gabon_2026.yaml`, `calcul_paie_gabon_reference.py` ; architecture `04` §1, §3, §15, §16.

**Livrables** (aucun import `odoo`) :
- `params.py` : `FiscalParams` (dataclass figée, tous les taux/plafonds/barèmes utiles, y compris `irpp_min_withholding` F14, plafonds d'exonération, arrondi espèces) + `load_from_yaml(path, date)` pour les tests (valeur applicable = dernière date ≤ date, RG06).
- `parts.py` : quotient familial (situation, enfants, enfants infirmes, demi-part spéciale, parts forcées 1 à 6,5 — RG03).
- `social.py` : assiette sociale, CNSS et CNAMGS salariales et patronales (PF, AT, AVID), plafonds, SMIG.
- `tax.py` : base TCS (option `tcs_deduct_cnamgs`, point 09-3), TCS, frais professionnels plafonnés, abattement, barème IRPP, parts, seuil F14, régularisation annuelle (dernier bulletin de l'année ou départ).
- `benefits.py` : avantages en nature.
- `exemptions.py` : `GainLine`, `exemptions(facts, params)` par ligne, registres `SOCIAL_CAPS` / `TAX_CAPS`, répartition au prorata dans un groupe, erreur explicite si groupe inconnu (patron 16). Logement en espèces : **pas de groupe** (point 09-5 ouvert) — le documenter.
- `rounding.py` (F2) : arrondi au multiple inférieur de l'arrondi société, reliquat reporté, versement intégral au solde de tout compte.
- `cash_breakdown.py` (F2) : billetage 10 000 / 5 000 / 2 000 / 1 000 / 500 (coupures en paramètre).
- `engine.py` : `PayslipFacts` → `compute(facts, params)` → `PayResult` (champs du fichier 04 §1 + détail par ligne des parts exclue/exonérée).

**Tests pytest** (`lib/tests/` ou `tests/test_core_*.py` exécutables sans Odoo) :
- les exemples chiffrés du fichier 04 §8 de la base ;
- le cas F16 : 590 000 → assiette sociale 555 000, imposable 450 000, CNSS 27 750, CNAMGS 11 100, TCS 13 058, IRPP 23 195, **net 514 897**, patronal CNSS 99 900, CNAMGS 22 755, FNH 16 650, CFP 2 775 ; variante « tout imposable » → net 486 617 ;
- jeux prioritaires du fichier 06 §3 (sous seuil TCS, marié 3 enfants au plafond CNSS, cadre au plafond de l'abattement, entré le 15, 13e mois dépassant 4 000 000, changement de taux au 01/01/2026 et au 17/07/2026) ;
- `test_rounding.py` : reliquat conservé sur 12 mois, somme versée = somme des nets ;
- `test_exemptions.py` : plafond partagé, prorata, `forced_taxable`, groupe inconnu ;
- **test de parité** : pour une grille de cas (paramétrée), `engine.compute` = `calcul_paie_gabon_reference.py` à 1 FCFA près ;
- test AST : aucun `import odoo` dans le package.

**Sortie** : `make test-core` vert, couverture ≥ 90 %.

---

## Étape 2.2 — Squelette du module et données

**Lire** : `05` §2.1 (manifeste), §2.2 (données), §2.4 (tableau des règles) ; `08` F4, F6, F14 ; base `05` (matrice des rubriques).

**Livrables** :
- `__manifest__.py`, `__init__.py`, `security/` (groupes, `ir.model.access.csv` vide prêt), `i18n/`.
- `tools/yaml_to_rule_parameters.py` → `data/hr_rule_parameters_data.xml` (une valeur datée par date d'effet, codes `l10n_ga_*`, idempotent, test qui régénère et compare au fichier versionné).
- `data/catalogue_rubriques_ga.csv` (~60 rubriques : code `GA_*`, libellé, catégorie, séquence, traitement social `subject/excluded/capped`, fiscal `taxable/exempt/capped`, groupes de plafond, proratisée, base congés, base rupture, colonne DAS, compte cible) construit depuis la matrice de la base `05` ; chaque classement cite sa source dans une colonne `source`.
- `tools/csv_to_salary_rules.py` → `data/hr_salary_rule_data.xml` ; règles `NET`, `GROSS`, `BASIC` standard réutilisées/conformes.
- Données : type de structure « Gabon : Employé », structure « Gabon — Employé », catégories, types d'entrée (`hr.payslip.input.type`, dont `GA_LOAN`), types de prestations `GA_HS_J`, `GA_HS_N`, `GA_HS_DIM`, `GA_HS_FER`, `GA_MAT`, `GA_AT`…, **12 types d'absence** F4 avec indicateur rémunéré / non rémunéré / pris en charge CNSS, séquence des prêts.
- Paramètre `l10n_ga_irpp_min_withholding` = 0 (F14).

**Tests** : `test_rule_codes_unique.py` (RG22 : un code par structure, aucune règle ne redéfinit `NET`, toute rubrique a un traitement social et fiscal, tout groupe de plafond est connu du registre du noyau) ; installation sur base neuve.

---

## Étape 2.3 — Modèles, adaptateur et règles liées au noyau

**Lire** : `05` §2.2, §2.3, §2.4 ; `04` §2 (Adapter), §3 ; `08` F7, F16 ; résultats sprint 0 (points 1, 2, 10, 11, 12, 13).

**Livrables** :
- `models/hr_version.py` : champs du tableau `05` §2.2 (enfants infirmes, demi-part, `l10n_ga_tax_parts` calculé stocké, parts forcées + motif, n° CNAMGS, NIF, code nationalité calculé, codes emploi/niveau, trajets, véhicule de fonction, `l10n_ga_payment_mode`) ; les champs `l10n_ga_agreement_id` / `l10n_ga_grade_id` sont ajoutés à l'étape 2.4.
- `models/res_company.py` : NIF, n° CNSS/CNAMGS employeur, centre des impôts, segment, option CFP, part FNH, `l10n_ga_cash_rounding` (500), plafond d'encours des prêts, options des points 09 non tranchés.
- `models/hr_salary_rule.py` : `l10n_ga_social_base`, `l10n_ga_tax_base`, `l10n_ga_social_cap_group`, `l10n_ga_tax_cap_group`, `l10n_ga_prorate`, base congés, base rupture, colonne DAS.
- `models/hr_payslip.py` : `_l10n_ga_facts()`, `_l10n_ga_params()`, `_l10n_ga_compute(code, categories, result_rules)` avec cache du `PayResult` par bulletin, `_l10n_ga_paid_ratio()`, `_l10n_ga_days_worked()`, cumuls annuels (`_l10n_ga_ytd`), `l10n_ga_payment_date` ; **champs figés F7** remplis à la validation (parts utilisées, plafonds et bases appliqués, cumuls `l10n_ga_ytd_*`).
- `models/hr_payslip_line.py` : `l10n_ga_social_excluded`, `l10n_ga_tax_exempt` figés à la validation (F16).
- Règles fiscales en une ligne (`result = -payslip._l10n_ga_compute('irpp', ...)`), selon les noms réels vérifiés au sprint 0.
- Vues : fiche salarié (`hr.view_employee_form`, groupe `hr_family_group` et page `payroll_information`), société (onglet « Gabon — Paie et fiscalité »), règle salariale (bloc « Fiscalité Gabon »).

**Tests** : `test_tax_parts.py` ; `test_payslip_ga.py` (TransactionCase) : un bulletin complet par profil du fichier 06 §3, version changée en cours d'année (nombre d'enfants), bulletins de décembre 2025 / janvier 2026 / juillet 2026 (paramètres datés), comparaison ligne à ligne au noyau ; bulletin validé puis paramètre modifié → valeurs figées inchangées ; cas F16 de bout en bout dans Odoo.

---

## Étape 2.4 — Conventions, grilles, heures supplémentaires, absences

**Lire** : `03` RG04, RG18 ; `08` F4, F5 ; base `05` (ancienneté, congés) ; point 09-11.

**Livrables** : `l10n_ga.collective.agreement` (règle d'ancienneté : début, taux de début, pas annuel, plafond), `l10n_ga.overtime.rate` (tranches, période jour/nuit/dimanche/férié, taux — **aucune valeur par défaut**, point 09-11), `l10n_ga.agreement.grade` (catégorie, échelon, minimum, taux horaire, date d'effet) ; champs `l10n_ga_agreement_id`, `l10n_ga_grade_id` sur `hr.version` ; données de convention d'exemple marquées comme exemple ; `GA_ANC` selon la convention ; `BASIC` proratisé par les prestations (`worked_days`), jamais par une retenue ajoutée (B2) ; `GA_CONGE` (allocation de congé) ; lien types de congés ↔ types de prestations ; contrôle bloquant salaire < minimum de grille ; vues et menus.

**Tests** : `test_absences.py` (chaque type d'absence : effet sur `BASIC`, sur `GA_CONGE`, maternité/AT subrogées) ; ancienneté (début, pas, plafond) ; grille (salaire sous le minimum refusé).

---

## Étape 2.5 — Prêts salariés (F1) et indemnités récurrentes (F15)

**Lire** : `08` F1, F15 ; `04` §12 (Specification) ; `03` RG19-RG21, RG28 ; sprint 0 points 6 et 9 (si `hr.salary.attachment` accepte les gains, **l'étendre** au lieu de créer le modèle, ADR-16).

**Livrables** :
- `l10n_ga.employee.loan` + `.line` (`mail.thread`, séquence, états brouillon / approuvé / en cours / soldé / annulé ; échéances à payer / retenue / reportée), octroi par spécifications combinables (ancienneté, mensualité ≤ 40 % du net, encours ≤ plafond société — valeurs en paramètres datés), dérogation RH motivée et tracée, remboursement anticipé, report d'échéance, solde restant proposé au solde de tout compte ; entrée `GA_LOAN` alimentée par les échéances de la période ; échéance « retenue » à la validation du bulletin (RG21).
- `l10n_ga.employee.allowance` : salarié, société, type d'entrée, mode (fixe / % du salaire de la version / quantité × taux), valeur, début, fin facultative, forcée imposable + motif ; non-chevauchement (RG28, `@api.constrains`) ; `hr.payslip._l10n_ga_allowance_inputs()` appelée avant le calcul (point d'appel vérifié au sprint 0) : crée/met à jour les entrées marquées `l10n_ga_allowance_id`, prorata des jours de validité ; **une entrée manuelle du même type remplace l'automatique** ; `forced_taxable` transmis au noyau.
- Vues (liste sur la fiche salarié, bouton intelligent « Indemnités », écrans des prêts), droits.

**Tests** : `test_loan.py` (octroi, refus, dérogation, échéancier, retenue, anticipé, départ) ; `test_allowance.py` (chevauchement refusé, prorata début/fin de mois, entrée manuelle prioritaire, % du salaire suit la version, forcée imposable sans motif refusée).

---

## Étape 2.6 — Import Excel (F3), contrôles avant paie (F8), arrondi espèces (F2), cumuls d'ouverture (F12)

**Lire** : `08` F2, F3, F8, F12 ; `04` §8, §13, §15 ; `03` RG23, RG25, RG26 ; ADR-18 (emplacement de `l10n_ga.check.issue`, sprint 0).

**Livrables** :
- Assistant `l10n_ga.payslip.input.import` (Pipes and Filters) : génération du modèle Excel du lot (une ligne par salarié, une colonne par type d'entrée actif et par type d'HS), lecture `openpyxl`, étapes indépendantes testables (lecture, en-têtes, salarié, type, montant, appartenance au lot, doublons), aperçu des anomalies, écriture dans `hr.payslip.input` et `hr.work.entry` (heures décimales), recalcul du lot.
- `l10n_ga.check.issue` (selon ADR-18) + chaîne `PAYROLL_CHECKS` exécutée sur le lot avant calcul (sans n° CNSS, NIF, situation, date d'embauche ; parts forcées sans motif ; sous le minimum de grille ; compte bancaire manquant pour virement ; pas de version sur la période ; échéance de prêt > 40 % du net ; indemnité forcée imposable sans motif) ; lot bloqué s'il reste une anomalie bloquante (RG26) ; `hr_payslip_run.py` : date de paiement du lot, bouton « Contrôler ».
- Règles `GA_ROUND_PREV`, `GA_ROUND`, `GA_NET_PAY` après `NET` (qui reste unique) ; champ `l10n_ga_rounding_carry` ; reliquat versé au solde de tout compte.
- `l10n_ga.ytd.opening` (unique salarié × année, RG25) intégré aux cumuls (régularisation IRPP, compteur 4 000 000, DAS).

**Tests** : `test_input_import.py` (lignes fausses rejetées sans bloquer les bonnes, doublons, aperçu, décimales) ; contrôles (chaque règle de la chaîne) ; `test_rounding.py` côté Odoo sur 12 bulletins consécutifs ; bascule en cours d'année avec cumuls d'ouverture (régularisation IRPP juste).

---

## Étape 2.7 — Rapports : bulletin figé, livre de paie, virements, billetage

**Lire** : `08` F2, F7, F13 ; `04` §9 (Builder) ; RG24.

**Livrables** :
- `report/report_payslip_ga.xml` : bulletin PDF QWeb qui **ne lit que les champs figés du bulletin et ses lignes** (jamais la fiche du jour), mentions légales gabonaises, cumuls annuels, parts, bases.
- Livre de paie Excel (`xlsxwriter`, une ligne par bulletin, une colonne par rubrique du catalogue, totaux) + état des charges (CNSS par branche, CNAMGS, FNH, CFP, IRPP, TCS) rapproché des comptes 43x/44x si la compta est installée.
- État des virements par banque (une feuille par banque, `primary_bank_account_id`) et état de billetage des paies en espèces.
- `constant_memory` pour les gros volumes ; menus et actions.

**Tests** : bulletin validé, fiche salarié modifiée, PDF régénéré identique (comparaison du HTML rendu) ; livre de paie : totaux = somme des lignes ; billetage : somme des coupures = somme des `GA_NET_PAY` espèces.

---

## Fin de CHAQUE étape (obligatoire)

Applique le protocole de complétude `CLAUDE.md` §7 **sur le périmètre de l'étape** : inventaire attendu/réel, matrice RG/F/ADR → code → test, chasse aux trous, `make lint`, `make test-core`, `make test MODULE=l10n_ga_hr_payroll` sur base neuve, `make upgrade`, recette chiffrée, complétion des manques jusqu'à zéro, rapport `docs/completude/l10n_ga_hr_payroll_2.X.md`, commit, mise à jour de `docs/PROGRESS.md`. Puis attends mon « go ».

Après l'étape 2.7 : lance `prompts/99_completude.md` sur **tout le module** avant de passer au module suivant.
