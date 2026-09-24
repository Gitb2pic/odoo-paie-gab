# 08 — Évolutions de la V2 après le benchmark

Source : `07_benchmark_hr_payroll_gb_vs_v2.md` (analyse du module freelance `hr_payroll_gb`, de l'addon V1 `l10n_ga_dgi_edi` et de la conception V2). Ce fichier liste les fonctionnalités ajoutées à la V2, leur conception, et renvoie aux fichiers d'architecture modifiés (01 à 06). Version 1.1 de l'architecture — 23/09/2026.

## 1. Synthèse

Le benchmark confirme les choix de fond de la V2 (paramètres datés, noyau fiscal testé, moteur de déclarations figé, comptabilisation SYSCOHADA) mais révèle **cinq trous de conception** (§ 6.3 du benchmark) et plusieurs fonctions métier que le freelance et la V1 couvrent déjà et que la V2 ne doit pas perdre. Quatorze évolutions sont retenues ; elles ajoutent un module de reprise, sept modèles, et avancent une partie des déclarations comptables en V1.

| Réf. | Fonctionnalité ajoutée | Origine dans le benchmark | Module | Version |
|---|---|---|---|---|
| F1 | Prêts salariés avec échéancier et contrôles d'octroi | § 5 (prêts freelance), § 6.3 point 1 | `l10n_ga_hr_payroll` | V1.0 |
| F2 | Mode de paiement par salarié, arrondi des paies en espèces à 500 FCFA avec report du reliquat, billetage, état des virements par banque | § 5 (SURPL/NETM), B1, § 6.3 point 2 | `l10n_ga_hr_payroll` | V1.0 |
| F3 | Import Excel des variables mensuelles vers les entrées de bulletin et les prestations | § 5 (import archive), § 6.3 point 3 | `l10n_ga_hr_payroll` | V1.0 |
| F4 | Absences et congés gabonais (12 types) avec proratisation du salaire par les prestations | § 5 (types de congés), B2 | `l10n_ga_hr_payroll` | V1.0 |
| F5 | Grille conventionnelle (catégories, échelons, minimum, taux horaire) et contrôle du salaire minimum ; ancienneté par convention | M8, § 4.3 (ancienneté) | `l10n_ga_hr_payroll` | V1.0 |
| F6 | Catalogue des ~60 rubriques gabonaises reclassées (assiette sociale, fiscale, plafond, colonne DAS) et test d'unicité des codes | § 5 (nomenclature), M4, M5, M6 | `l10n_ga_hr_payroll` | V1.0 |
| F7 | Bulletin figé : valeurs imprimées lues sur le bulletin (parts, plafonds, bases, cumuls annuels), jamais sur la fiche du jour | § 4.3 (bulletin PDF), M7 | `l10n_ga_hr_payroll` | V1.0 |
| F8 | Contrôles avant paie (écran des anomalies salariés) partagés avec l'écran « Contrôle DAS » | § 5 (écran anomalies), § 6.1 | `l10n_ga_hr_payroll` + `l10n_ga_dgi_edi` | V1.0 |
| F9 | DAS complète dès la V1 : ID19 à ID26, avec retenues fournisseurs 9,5 % et 20 % (ID18, ID27) et classement des bénéficiaires | § 6.3 point 4, § 6.1 | `l10n_ga_dgi_edi` + `l10n_ga_dgi_edi_account` (partie V1) | V1.0 |
| F10 | Classeurs officiels DGI `.xlsm` remplis en conservant les macros | § 6.1 | `l10n_ga_dgi_edi` | V1.0 |
| F11 | Plusieurs quittances par déclaration, reprises automatiquement dans la grille ID22 | § 6.1 (deux quittances par ID10) | `l10n_ga_dgi_edi` | V1.0 |
| F12 | Reprise des données depuis `hr_payroll_gb` et migration des déclarations V1, cumuls d'ouverture de l'année | § 6.3 point 5, § 6.2 | nouveau `l10n_ga_hr_payroll_migration` + scripts de migration de `l10n_ga_dgi_edi` | V1.0 |
| F13 | Livre de paie et état des charges sociales et fiscales (Excel) | § 2 (couverture paie), § 5 (livre de paie maison à ne pas reprendre) | `l10n_ga_hr_payroll` | V1.0 |
| F14 | Seuil minimal de retenue IRPP en paramètre daté (valeur 0 par défaut) | M10 | `l10n_ga_hr_payroll` | V1.0 |

## 2. Conception des évolutions

### F1 — Prêts salariés

Modèles : `l10n_ga.employee.loan` (salarié, société, montant, date d'octroi, nombre d'échéances, mensualité, état brouillon / approuvé / en cours / soldé / annulé, dérogation RH et motif) et `l10n_ga.employee.loan.line` (échéance : date, montant, état à payer / retenue / reportée, bulletin qui l'a retenue).
Règles d'octroi (patron Specification, paramètres datés) : ancienneté ≥ 2 ans, mensualité ≤ 40 % du salaire net, encours ≤ plafond société ; toute règle peut être levée par une dérogation RH tracée (`mail.thread`).
Paie : l'entrée de bulletin `GA_LOAN` est alimentée par les échéances dues sur la période ; à la validation du bulletin, l'échéance passe à « retenue » ; au départ du salarié, le solde restant est proposé en retenue sur le solde de tout compte, dans la limite de la quotité saisissable.
Repris du freelance : logique métier et contrôles (`hr_employee_loan.py`), réécrits avec `company_id`, droits et tests.

### F2 — Modes de paiement, arrondi espèces, billetage, virements

Sur `hr.version` : `l10n_ga_payment_mode` (virement, espèces, chèque) ; le compte bancaire vient du standard (`hr.employee.primary_bank_account_id` ✔ Odoo 19).
Sur `res.company` : `l10n_ga_cash_rounding` (500 FCFA par défaut, 0 = pas d'arrondi).
Règles, toutes après `NET` et sans jamais le remplacer (correction de B1) :

| Code | Calcul |
|---|---|
| `NET` | règle standard unique, quel que soit le mode de paiement |
| `GA_ROUND_PREV` | reliquat reporté du bulletin précédent (lu sur ce bulletin, champ `l10n_ga_rounding_carry`) |
| `GA_ROUND` | espèces seulement : `NET + GA_ROUND_PREV` arrondi à l'unité inférieure de 500 ; le reliquat est stocké sur le bulletin |
| `GA_NET_PAY` | montant à verser = `NET + GA_ROUND_PREV − reliquat` (espèces) ou `NET` (virement, chèque) |

Sorties : état des virements par banque (Excel, une feuille par banque) et état de billetage des paies en espèces (coupures de 10 000, 5 000, 2 000, 1 000 et 500 FCFA).

### F3 — Import Excel des variables mensuelles

Assistant `l10n_ga.payslip.input.import` (patron Pipes and Filters) : 1) modèle Excel généré pour le lot (une ligne par salarié, une colonne par type d'entrée actif, colonnes d'heures supplémentaires par type) ; 2) lecture `openpyxl` ✔ (dépendance d'Odoo 19) ; 3) validation (matricule connu, type d'entrée existant, montant numérique, salarié dans le lot) ; 4) aperçu des anomalies ; 5) création des `hr.payslip.input` 🔒 et des prestations `hr.work.entry` ✔ pour les heures ; 6) recalcul du lot. Les heures acceptent les décimales (correction du freelance, heures entières).

### F4 — Absences et congés gabonais

Types de prestations `hr.work.entry.type` ✔ et types de congés `hr.leave.type` ✔ (liste reprise du freelance) : congé payé, maladie avec certificat, maladie non payée, maternité (IJ CNSS, subrogation), accident du travail, naissance, mariage, décès (circonstances), absence justifiée non payée, absence injustifiée, mise à pied disciplinaire, sanction.
Chaque type porte un indicateur « rémunéré / non rémunéré / pris en charge CNSS ». La règle `BASIC` = salaire mensuel × heures rémunérées / heures du mois (correction de B2) ; les jours de congé payé sortent du salaire de base et sont payés par l'allocation de congé `GA_CONGE` (fichier 05 de la base) ; la maternité et l'AT alimentent une créance CNSS en cas de subrogation.

### F5 — Grille conventionnelle

Modèle `l10n_ga.agreement.grade` (convention, catégorie, échelon, salaire minimum mensuel, taux horaire, date d'effet) rattaché à `hr.version` par `l10n_ga_grade_id`. Le salaire (`wage` standard, jamais redéfini : correction de M8) reste individuel ; un contrôle bloquant signale un salaire inférieur au minimum de la grille. La prime d'ancienneté suit la règle de la convention (début, pas annuel, plafond) au lieu du 1 % sans plafond du freelance.

### F6 — Catalogue des rubriques

Fichier de données `hr_salary_rule_data.xml` généré à partir d'un catalogue tabulaire (`data/catalogue_rubriques_ga.csv` : code, libellé, catégorie, assiette sociale, assiette fiscale, paramètre de plafond, base congés, base rupture, colonne DAS, compte) qui reprend les ~60 primes et indemnités du freelance, reclassées selon la matrice du fichier 05 de la base de connaissance.
Tests : un code par rubrique et par structure (corrige M5 et M6, où deux règles de même code s'annulent) ; toute rubrique a une assiette sociale et fiscale renseignée ; aucune règle ne redéfinit `NET`.

### F7 — Bulletin figé

Champs stockés sur `hr.payslip` 🔒 à la validation : parts fiscales utilisées, situation, plafonds CNSS et CNAMGS appliqués, bases (sociale, TCS, IRPP), avantages en nature par nature, cumuls annuels (`l10n_ga_ytd_gross`, `_taxable`, `_irpp`, `_tcs`, `_cnss`, `_bonus_exempt`). Le rapport `report_payslip_ga` ne lit que ces champs et les lignes : un ancien bulletin réimprimé reste identique. La DAS lit les mêmes valeurs, ce qui supprime l'écart bulletin / DAS relevé en M7.

### F8 — Contrôles avant paie

La chaîne de contrôles (patron 8 du fichier 04) s'applique désormais à deux périmètres : le lot de paie avant calcul (salarié sans n° CNSS, NIF, situation familiale ou date d'embauche ; parts forcées sans motif ; salaire sous le minimum de grille ; compte bancaire manquant pour un virement ; version absente sur la période ; prêt dont l'échéance dépasse 40 % du net) et la déclaration. Les anomalies sont stockées dans un modèle unique `l10n_ga.check.issue` (périmètre, gravité, code, message, enregistrement concerné), affiché sur le lot et dans l'écran « Contrôle DAS » repris de la V1.

### F9 — DAS complète et retenues fournisseurs dès la V1

Le périmètre V1 couvre toute la DAS (ID19 à ID26), comme la V1 existante, au lieu d'attendre la V2.0. Conséquence : une partie de `l10n_ga_dgi_edi_account` passe en V1.0.

| Élément | Conception |
|---|---|
| Classement des bénéficiaires | champs `res.partner` : `l10n_ga_fee_category` (A administrateurs/commissaires, B courtiers/intermédiaires, C honoraires), `l10n_ga_is_resident`, `l10n_ga_zone` (CEMAC / hors CEMAC), `l10n_ga_vat_subject` |
| Retenues 9,5 % et 20 % | taxes de retenue fournisseur `l10n_ga_ras_095` et `l10n_ga_ras_20`, appliquées au paiement via `l10n_account_withholding_tax` ✔ (module Odoo 19 « Withholding Tax on Payment ») ou, à défaut, en taxes négatives sur facture |
| ID18 / ID27 (mensuels) | somme des retenues du mois par bénéficiaire |
| ID23 / ID24 / ID26 (annuels) | agrégation des lignes de factures fournisseurs payées dans l'année, par classement du bénéficiaire, et des retenues |
| Règle anti-double retenue | un non-résident ne subit que la retenue de 20 %, jamais 9,5 % en plus (anomalie du fichier DAS v3) |

### F10 — Classeurs officiels `.xlsm`

Les classeurs DGI de la V1 (`edi-annexe-ID19/21/23/26.xlsm`) deviennent les gabarits des types de déclaration. Le rendu Excel utilise `openpyxl` avec `keep_vba=True` ✔ pour remplir un gabarit existant (xlsxwriter ne sait qu'écrire des fichiers neufs) ; `xlsxwriter` reste utilisé pour les états générés de zéro (livre de paie, virements, billetage). Le patron Builder expose les deux moteurs derrière la même interface.

### F11 — Quittances multiples

Nouveau modèle `l10n_ga.declaration.payment` (déclaration, date, montant, n° de quittance, rubrique RS ou FNH, pièce comptable). Une déclaration peut avoir plusieurs paiements (la V1 gère déjà deux quittances par ID10). La grille des versements de l'ID22 et le contrôle « total versé = total retenu » lisent ces paiements.

### F12 — Reprise des données et migration

| Volet | Conception |
|---|---|
| Module one-shot `l10n_ga_hr_payroll_migration` | installé le temps de la bascule puis désinstallé ; dépend de `l10n_ga_hr_payroll` ; lit les tables de `hr_payroll_gb` par SQL (le module freelance peut être désinstallé ensuite) |
| Correspondances (patron Data Mapper) | table `l10n_ga.migration.map` : code freelance → code `GA_*`, catégorie freelance → grade de convention, champs société et salarié (NINEA, CMU et autres champs étrangers ignorés) |
| Données reprises | salariés et versions (situation, enfants, n° CNSS, mode de paiement), grades, prêts en cours avec échéances restantes, variables du mois en cours |
| Cumuls d'ouverture | modèle `l10n_ga.ytd.opening` (salarié, année, brut, imposable, IRPP, TCS, CNSS, gratifications exonérées, période couverte) : alimente la régularisation IRPP, le compteur des 4 000 000 et la DAS de l'année de bascule |
| Migration de la V1 | le module V2 garde le nom technique `l10n_ga_dgi_edi` ; ses scripts `migrations/19.0.2.0.0/` convertissent `dgi.id10`, `dgi.id20`, `dgi.id22`, `dgi.dts`, `dgi.edi.declaration` en `l10n_ga.declaration` figées (état « déposée » ou « payée »), pièces jointes et quittances comprises, puis suppriment les anciens modèles |
| Contrôle de bascule | rapport de rapprochement : cumuls repris = cumuls des bulletins `hr_payroll_gb` de l'année, par salarié et par rubrique |

### F13 — Livre de paie et état des charges

Livre de paie Excel par période (une ligne par bulletin, une colonne par rubrique du catalogue, totaux) et état des charges (CNSS par branche, CNAMGS, FNH, CFP, IRPP, TCS) rapproché des comptes 43x et 44x. Ce sont des rapports sur les lignes de bulletins validés, sans table propre.

### F14 — Seuil minimal de retenue IRPP

Le freelance ne retient pas l'IRPP ≤ 1 000 FCFA, sans base légale trouvée. La V2 crée le paramètre daté `l10n_ga_irpp_min_withholding` à 0 : le comportement est désactivé par défaut et documenté si le client le demande.

## 3. Impacts sur l'architecture (résumé des modifications)

| Fichier | Modification |
|---|---|
| 00 | ADR-11 à ADR-15 ; vue d'ensemble avec le module de reprise |
| 01 | 5 modules ; `l10n_ga_dgi_edi_account` scindé en périmètre V1.0 (retenues, DAS honoraires) et V2.0 ; flux mensuel avec import, prêts, arrondi |
| 02 | Nouveaux cas d'utilisation, classes (prêt, grade, paiement de déclaration, anomalie, cumuls d'ouverture, import), séquences import et bascule |
| 03 | Règles de gestion RG18 à RG27 ; entités PRET, ECHEANCE, GRADE, QUITTANCE, ANOMALIE, CUMUL_OUVERTURE ; PAIEMENT passe de (0,1) à (0,n) |
| 04 | Patrons 12 à 15 : Specification (octroi de prêt), Pipes and Filters (import), Data Mapper (reprise), report de reliquat |
| 05 | Nouveaux points d'intégration (`primary_bank_account_id`, `l10n_account_withholding_tax`, `openpyxl`, scripts de migration) |
| 06 | Arborescence, tests (unicité des codes, bascule), feuille de route avec phase 0 et reprise |
