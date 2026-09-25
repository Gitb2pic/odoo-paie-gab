# Avancement — Paie Gabon & déclarations DGI V2

Mis à jour le 25/09/2026 (complétude C-2).

## Étapes

| Étape | Module | Contenu | État | Complétude | Rapport |
|---|---|---|---|---|---|
| Sprint 0 | socle | dépôt, outillage, vérifications Enterprise (14 points) | **terminé** | 100 % | `docs/completude/sprint0.md` |
| 2.1 | `l10n_ga_hr_payroll` | noyau fiscal pur `lib/ga_fiscal_core` | **terminé** | 100 % (334 tests, couverture 100 %, parité oracle ≤ 1 FCFA) | `docs/completude/l10n_ga_hr_payroll_2.1.md` |
| 2.2 | `l10n_ga_hr_payroll` | squelette du module et données | **terminé** | 100 % (19/19 ; 62 rubriques, 50 paramètres datés ; 18 tests Odoo, 55 tests d'outillage, noyau 368 tests couverture 100 % ; F16 rejoué sur les données générées) | `docs/completude/l10n_ga_hr_payroll_2.2.md` |
| 2.3 | `l10n_ga_hr_payroll` | modèles, adaptateur et règles liées au noyau | **terminé** | 100 % (22/22 ; 50 tests Odoo, 63 d'outillage, noyau 369 tests couverture 100 % ; F16 net 514 897 dans Odoo ; install. sur base existante et désinstallation propres) | `docs/completude/l10n_ga_hr_payroll_2.3.md` |
| 2.4 | `l10n_ga_hr_payroll` | conventions, grilles, heures supplémentaires, absences | **terminé** | 100 % (18/18 ; 69 tests Odoo, 64 d'outillage, noyau 398 tests couverture 100 % ; 12 absences, ancienneté, grille bloquante, heures sup. sans taux par défaut) | `docs/completude/l10n_ga_hr_payroll_2.4.md` |
| 2.5 | `l10n_ga_hr_payroll` | prêts salariés (F1), indemnités récurrentes (F15) | **terminé** | 100 % (20/20 ; 108 tests Odoo, 64 d'outillage, noyau 439 tests couverture 100 % ; prêts par spécifications, quotité saisissable, indemnités = ajustements datés) | `docs/completude/l10n_ga_hr_payroll_2.5.md` |
| 2.6 | `l10n_ga_hr_payroll` | import Excel (F3), contrôles avant paie (F8), arrondi espèces (F2), cumuls d'ouverture (F12) | **terminé** | 100 % (22/22 ; 156 tests Odoo, 65 d'outillage, noyau 466 tests couverture 100 % ; lot bloqué RG26, F16 espèces 514 500 + reliquat 397, bascule en juillet = année complète) | `docs/completude/l10n_ga_hr_payroll_2.6.md` |
| 2.7 | `l10n_ga_hr_payroll` | rapports : bulletin figé, livre de paie, virements, billetage | **terminé** (bulletin repris au format du modèle d'Alex, 2.7 b) — en attente du « go » pour C-1 | 100 % (16/16 + 9/9 écarts ; 178 tests Odoo, 72 d'outillage, noyau 483 tests couverture 100 % ; bulletin réimprimé identique ; D-47 à confirmer) | `docs/completude/l10n_ga_hr_payroll_2.7.md` |
| C-1 | `l10n_ga_hr_payroll` | complétude du module (`prompts/99_completude.md`) | **terminé** | 100 % (0 manque ; lint 0 erreur, noyau 483 tests couverture 100 %, 178 tests Odoo sur base neuve et en mise à jour) | `docs/completude/l10n_ga_hr_payroll_C-1.md` |
| 3 | `l10n_ga_hr_payroll_account` | comptabilisation SYSCOHADA | **terminé** | 100 % (18/18 ; 28 tests Odoo, F16 compte par compte écart 0 ; installation sur société existante et désinstallation propres) | `docs/completude/l10n_ga_hr_payroll_account.md` |
| C-2 | `l10n_ga_hr_payroll_account` | complétude du module | **terminé** | 100 % (3 manques corrigés, dont SYSCEBNL validé sans écriture ; 32 tests du module, 210 tests paie + comptabilité installées ensemble) | `docs/completude/l10n_ga_hr_payroll_account_C-2.md` |
| 4.1 | `l10n_ga_dgi_edi` | moteur de déclarations | à faire | — | — |
| 4.2 | `l10n_ga_dgi_edi` | ID10, ID28, quittances multiples (F11) | à faire | — | — |
| 4.3 | `l10n_ga_dgi_edi` | DTS CNSS et CNAMGS | à faire | — | — |
| 4.4 | `l10n_ga_dgi_edi` | DAS ID19 à ID22, « Contrôle DAS », classeurs `.xlsm` | à faire | — | — |
| 4.5 | `l10n_ga_dgi_edi` | migration des déclarations V1 (ADR-12) | à faire | — | — |
| C-3 | `l10n_ga_dgi_edi` | complétude du module | à faire | — | — |
| 5 | `l10n_ga_dgi_edi_account` | ID18, ID27, ID23, ID24, ID26 | à faire | — | — |
| C-4 | `l10n_ga_dgi_edi_account` | complétude du module | à faire | — | — |
| 6 | `l10n_ga_hr_payroll_migration` | reprise `hr_payroll_gb` | à faire | — | — |
| C-5 | `l10n_ga_hr_payroll_migration` | complétude du module | à faire | — | — |

## ADR (sprint 0) — tous **acceptés** le 24/09/2026

| ADR | Objet | Fichier |
|---|---|---|
| ADR-16 | Indemnités contractuelles en lignes datées (`hr.salary.attachment`) | `docs/adr/ADR-16-indemnites-contractuelles-lignes-datees.md` |
| ADR-17 | Exonérations par ligne, plafonds par groupe (`SOCIAL_CAPS` / `TAX_CAPS`) | `docs/adr/ADR-17-exonerations-par-ligne-plafonds-par-groupe.md` |
| ADR-18 | `l10n_ga.check.issue` défini dans la paie, étendu par les déclarations | `docs/adr/ADR-18-check-issue-dans-la-paie.md` |
| ADR-19 | Points d'accroche Enterprise 19 corrigés (états, Observer, bulletin figé, comptes par société, règle courante) | `docs/adr/ADR-19-points-accroche-enterprise-19.md` |

## Bloquants et questions ouvertes

Voir `docs/decisions/ouvertes.md`. D-04 abandonné par Alex (24/09/2026). Actions attendues d'Alex : D-05 (avant l'étape 6), D-07 (avant l'étape 4.4). Décidés : D-18 à D-22 (2.3), D-23 à D-28 (2.4), D-29 à D-37 (2.5), D-38 à D-46 (2.6), D-47 à D-53 (2.7, go anticipé ; D-47 mentions du bulletin à confirmer), D-54 à D-57 (2.7 b, bulletin au format du modèle), D-58 à D-64 (3, comptabilisation). Dette de 2.5 (régularisation IRPP sans cumuls d'ouverture) soldée par F12.

## Prochaine étape

Étape 4.1 — `l10n_ga_dgi_edi`, moteur de déclarations (`prompts/04_l10n_ga_dgi_edi.md`) : plan `docs/plans/4.1.md` à présenter, puis « go » d'Alex avant de coder. Démo possible : `make demo MODULE=l10n_ga_hr_payroll_account` (redémarre le service `odoo19`, sur accord explicite d'Alex).
