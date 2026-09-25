# Plan — FIX 01 : base horaire du salaire de base (173,33 h)

Date : 25/09/2026 — module `l10n_ga_hr_payroll` — statut : **en attente du « go » d'Alex** (et de sa réponse à D-104).

Sources : prompt FIX 01 ; arrêté 016/MTEPS art. 5 ; base `05` §2 (taux horaire = salaire / 173,33) ; YAML `heures_mensuelles_reference: 173.33` ; `08` F3, F4, F7.

## 1. Constat dans le code (vérifié)

| Point | Constat | Preuve |
|---|---|---|
| Salaire de base | `result = payslip.paid_amount` | `l10n_ga_hr_payroll/data/hr_salary_rule_data.xml:16` |
| `paid_amount` | Σ `amount` des prestations du bulletin | `E/hr_payroll/models/hr_payslip.py:1695-1704`, propriété `:961-964` |
| Montant d'une prestation | taux = `contract_wage / Σ heures des prestations hors heures sup.` (heures **du calendrier** : 184 h en janvier 2025, 160 h en février), montant = taux × heures × `amount_rate` si `is_paid`, sinon 0 ; `OUT` (hors contrat) = 0 | `E/hr_payroll/models/hr_payslip_worked_days.py:36-56` |
| Prestations non payées | `is_paid` faux si le type est dans `struct.unpaid_work_entry_type_ids` (congé payé `GA_CP`, maladie non payée, absences non rémunérées : `unpaid_structure_ids` de la structure Gabon) ; maternité / AT sans subrogation : faux (F4, D-26) | `E/hr_payroll/models/hr_payslip_worked_days.py:28-34` ; `models/hr_payslip_worked_days.py` ; `data/hr_work_entry_type_data.xml:54-148` |
| Hors contrat | prestation `OUT` (heures du calendrier de référence hors période du contrat) | `E/hr_payroll/models/hr_payslip.py:920-959` |
| Paramètre 173,33 | **existe** : `l10n_ga_hours_month_ref` (YAML `heures_mensuelles_reference`) — rien à ajouter | `lib/ga_fiscal_core/param_codes.py:51`, `data/hr_rule_parameters_data.xml:32` |

## 2. Usages d'un taux horaire ou d'un prorata d'heures (grep « wage / heures »)

| Usage | Aujourd'hui | Après correctif |
|---|---|---|
| Salaire de base `BASIC` | `paid_amount` (taux du calendrier) | `payslip._l10n_ga_basic_amount()` : quantité `H_REF − H_RETIREES` × `TAUX_H` (montant = `wage` exact si rien n'est retiré) |
| Heures supplémentaires | `_l10n_ga_hourly_rate()` = `wage / l10n_ga_hours_month_ref` (déjà juste) | **fonction unique** `_l10n_ga_hourly_rate()` réutilisée partout |
| Part payée du mois (indemnités proratisées, SMIG de présence) | `paid_amount / wage` | `_l10n_ga_basic_amount() / wage` |
| Maintien de salaire du congé payé (`GA_CONGE`) | prorata `heures de congé / heures du calendrier` | heures de congé / `H_REF` (même base que la ligne de base) |
| Bulletin imprimé (ligne salaire de base, ligne « absences ») | base = heures du calendrier, taux = `wage / heures du calendrier` | base = quantité figée de `BASIC`, taux = `TAUX_H` figé |
| En-tête « Horaires » | Σ heures des prestations | quantité figée de la ligne `BASIC` (F7) |

`TAUX_H` exposé une seule fois : `hr.payslip._l10n_ga_hourly_rate()` (déjà utilisée par les heures sup.). Le calcul pur (quantité, montant) va dans le noyau : `ga_fiscal_core/basic.py` → `basic_hours(h_ref, h_removed)`, `basic_amount(wage, h_ref, h_removed)` (sans import `odoo`, testé en pytest).

## 3. Règle cible

```
H_REF      = l10n_ga_hours_month_ref (paramètre daté, 173,33)
TAUX_H     = wage / H_REF
H_RETIREES = Σ heures des prestations hors heures sup. non payées par la règle de base
             (is_paid faux : absences non rémunérées, congé payé → GA_CONGE, CNSS sans subrogation)
             + heures hors contrat (OUT) — méthode (a), ou prorata (b), selon l'option société (D-104)
QUANTITE   = max(0, H_REF − H_RETIREES)
MONTANT    = wage si H_RETIREES == 0, sinon arrondi_franc(QUANTITE × TAUX_H)
```

Les prestations et le calendrier ne sont pas modifiés (ils restent la source des heures réelles).

## 4. Fichiers

| Fichier | Modification |
|---|---|
| `lib/ga_fiscal_core/basic.py` (+ tests pytest) | quantité et montant de la ligne de base, méthodes (a) / (b) |
| `models/hr_payslip.py` | `_l10n_ga_basic_hours()`, `_l10n_ga_basic_amount()`, `_l10n_ga_paid_ratio()` et maintien du congé sur `H_REF` ; base et taux figés de `BASIC` dans `_l10n_ga_freeze_lines` / `_l10n_ga_line_print_values` ; lignes imprimées du salaire de base |
| `models/res_company.py`, `views/res_company_views.xml` | option `l10n_ga_entry_exit_hours` : (a) « Retirer les heures hors contrat » (défaut) / (b) « Prorata des heures payées » |
| `data/hr_salary_rule_data.xml` (+ catalogue CSV) | `BASIC` : `result = payslip._l10n_ga_basic_amount()` |
| `report/report_payslip_ga.xml` | « Horaires » = quantité figée de `BASIC` |
| `tests/test_basic_hours.py` | T1 à T10 |

## 5. Tests (TDD, rouges avant le code)

Salarié fictif, contrat au 01/07/2024, 130 000, célibataire, 2 enfants ; responsabilité 200 000, représentation 100 000, rendement 62 000 (`BONUS_4M`), transport 35 000 (2 trajets) ; calendrier de 40 h.

| # | Cas | Attendu |
|---|---|---|
| T1 | janvier 2025 complet (184 h) | quantité 173,33 ; taux 750,01 ; 130 000 |
| T2 | février 2025 complet (160 h) | idem, même taux |
| T3 | janvier, 1 jour non payé | 165,33 ; 124 000 |
| T4 | janvier, absence non payée tout le mois | 0 ; 0 ; jamais négatif |
| T5 | 10 h sup. en janvier et en février | même taux de base 750,01, puis majoration de la convention |
| T6 | congé payé de 2 jours en janvier | 16 h retirées de la base, payées par `GA_CONGE` (maintien sur la même base horaire) |
| T7 | entrée le 16/01/2025 | méthode (a) par défaut ; (a) et (b) testées |
| T8 | PDF du bulletin T1 validé | « Horaires » 173,33 ; réimpression identique après modification du contrat (F7) |
| T9 | non-régression T1 | assiette 492 000 ; CNSS 12 300 ; CNAMGS 9 840 ; imposable 130 000 ; non imposable 397 000 ; base TCS 107 860 ; TCS 0 ; IRPP 0 ; net 504 860 (rejoué avec `calcul_paie_gabon_reference.py`) |
| T10 | statique | aucune règle ni méthode ne divise `wage` par des heures hors `_l10n_ga_hourly_rate()` ; aucun littéral 173,33 |

## 6. Point à trancher par Alex (D-104)

Entrée ou sortie en cours de mois :
- **(a)** `H_REF − heures hors contrat` (plancher 0), comme une absence — **défaut proposé** (cohérent avec le traitement des absences, lisible sur le bulletin) ;
- **(b)** `H_REF × heures payées / heures prévues du mois` (prorata : un mois de 184 h ou de 160 h donne le même pourcentage de salaire pour la même fraction de mois).

Les deux derrière une option société (règle d'or 13), (a) par défaut.

## 7. Risques

- Les bulletins **déjà validés** gardent leurs lignes figées (F7) : pas de recalcul rétroactif.
- La part payée change pour les salariés absents (indemnités proratisées, plancher SMIG) : couvert par T3, T4, T6, T9 et la suite existante (178 tests paie).
- Commits : `test(l10n_ga_hr_payroll): base horaire 173,33`, puis `fix(l10n_ga_hr_payroll): taux horaire unique sur 173,33 h` ; complétude → `docs/completude/l10n_ga_hr_payroll_fix_01.md`.
