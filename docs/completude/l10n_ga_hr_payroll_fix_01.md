# Complétude — FIX 01 : base horaire du salaire de base (173,33 h)

Date : 25/09/2026 — plan `docs/plans/fix_01_base_horaire.md` ; « go avec tes recommandations » (D-104 : méthode (a) par défaut).

## Score

**10 / 10 cas attendus présents et testés (100 %)** ; 188 tests de la paie sur base neuve et en mise à jour ; **331 tests** verts avec les quatre modules Gabon ; noyau 490 tests, couverture 100 %.

## C1 — Inventaire

| Élément | État | Fichier |
|---|---|---|
| Calcul pur : taux horaire unique, quantité (méthodes a / b), montant exact sur un mois complet | présent | `lib/ga_fiscal_core/basic.py` (+ `lib/tests/test_basic.py`, 7 tests) |
| Paramètre daté des heures de référence | déjà présent (`l10n_ga_hours_month_ref`, YAML `heures_mensuelles_reference`) | `data/hr_rule_parameters_data.xml:32` |
| `BASIC` = `payslip._l10n_ga_basic_amount()` (généré depuis le catalogue) | présent | `tools/csv_to_salary_rules.py`, `data/hr_salary_rule_data.xml:16` |
| Fonction unique du taux horaire `_l10n_ga_hourly_rate()` (heures sup., bulletin imprimé) | présent | `models/hr_payslip.py` |
| Part payée (indemnités proratisées, plancher SMIG) sur la même base | présent | `_l10n_ga_paid_ratio()` |
| Maintien du congé payé : heures de congé / 173,33 | présent | `_l10n_ga_leave_allowance()` |
| Base et taux de `BASIC` figés à la validation (F7) ; « Horaires » = quantité figée | présent | `_l10n_ga_line_print_values`, `_l10n_ga_report_data`, `_l10n_ga_basic_rows` |
| Option société entrée / sortie (a) / (b) | présent | `res_company.l10n_ga_entry_exit_hours`, vue société |

## C2 — Traçabilité (tests `tests/test_basic_hours.py`)

| # | Cas | Résultat |
|---|---|---|
| T1 / T2 | janvier (184 h) et février (160 h) 2025 complets | 173,33 h ; 750,01 ; 130 000 les deux mois ✔ |
| T3 | 1 jour non payé | 165,33 h ; 124 000 ✔ |
| T4 | mois entier non payé | 0 h ; 0 ; aucune valeur négative ✔ |
| T5 | 10 h sup. en janvier et en février | même taux, même montant (8 250) ✔ |
| T6 | congé payé de 2 jours | 157,33 h ; 118 000 ; `GA_CONGE` = maintien sur 16 h / 173,33 ✔ |
| T7 | entrée le 16/01/2025 (88 h hors contrat) | (a) 85,33 h → 63 999 ; (b) 173,33 × 96 / 184 → 67 826 ✔ |
| T8 | bulletin validé | « Horaires » 173,33, taux 750,01 ; identique après modification du contrat ✔ |
| T9 | non-régression | assiette 492 000, CNSS 12 300, CNAMGS 9 840, imposable 130 000, non imposable 397 000, base TCS 107 860, TCS 0, IRPP 0, net 504 860 ✔ |
| T10 | statique | aucun `wage /` hors `hourly_rate()`, aucun 173,33 littéral ✔ |

Tests existants mis à jour (le comportement corrigé change leurs attentes) : `test_absences` (16 h retirées de 173,33 au lieu de 16 / 176 du calendrier), `test_payslip_ga.test_hired_on_the_15th_prorated` (80 h hors contrat → 161 536).

## C3 — Chasse aux trous

Aucun `TODO` ; aucun `173,33` en dur ; seule `hourly_rate()` divise un salaire par des heures ; option société traduite ; `paid_amount` n'est plus utilisé que pour les salaires horaires (standard).

## C4 — Exécution

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test-core` | 73 + 490 tests, couverture 100 % |
| `make test MODULE=l10n_ga_hr_payroll` | 188 tests, 0 échec |
| `make upgrade MODULE=l10n_ga_hr_payroll` | 188 tests, 0 échec |
| quatre modules Gabon ensemble | 331 tests, 0 échec |

## C5 — Recette

T9 rejoué avec `calcul_paie_gabon_reference.py` (taux 2025 : CNSS 2,5 %, FNH 2 %) : assiette 492 000, CNSS 12 300, CNAMGS 9 840, base TCS 107 860, TCS 0, IRPP 0, net 504 860 — **écart 0**.

## Dette acceptée

- Bulletins validés **avant** le correctif : lignes figées sans base / taux de `BASIC` ; à la réimpression, « Horaires » reprend les heures du calendrier et la ligne de base n'affiche pas de taux (valeurs payées inchangées, pas de recalcul rétroactif).
- Hors périmètre, comme demandé : total « TOTAL BRUT » (20900), assiettes transport / rendement.
