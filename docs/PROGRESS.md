# Avancement — Paie Gabon & déclarations DGI V2

Mis à jour le 25/09/2026 (FIX 01).

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
| FIX 01 | `l10n_ga_hr_payroll` | salaire de base sur 173,33 h, taux horaire unique | **terminé** | 100 % (T1-T10 ; 188 tests paie, 331 avec les 4 modules ; T9 écart 0 avec le calculateur) | `docs/completude/l10n_ga_hr_payroll_fix_01.md` |
| 4.1 | `l10n_ga_dgi_edi` | moteur de déclarations | **terminé** | 100 % (24/24 ; 47 tests Odoo sur base neuve et en mise à jour, 258 avec paie + comptabilité ; F16 déclaré écart 0 ; installation sur base existante et désinstallation propres) | `docs/completude/l10n_ga_dgi_edi_4.1.md` |
| 4.2 | `l10n_ga_dgi_edi` | ID10, ID28, quittances multiples (F11) | **terminé** | 100 % (20/20 ; 66 tests Odoo sur base neuve et en mise à jour, 277 avec paie + comptabilité ; F16 déclaré écart 0 ; D-74 NIF à confirmer) | `docs/completude/l10n_ga_dgi_edi_4.2.md` |
| 4.3 | `l10n_ga_dgi_edi` | DTS CNSS et CNAMGS | **terminé** (+ PDF au format Excel, 25/09) | 100 % (16/16 ; 75 tests Odoo sur base neuve et en mise à jour, 286 avec paie + comptabilité ; T3 F16 écart 0 ; D-83 format des portails à confirmer) | `docs/completude/l10n_ga_dgi_edi_4.3.md` |
| 4.4 | `l10n_ga_dgi_edi` | DAS ID19 à ID22, « Contrôle DAS », classeurs `.xlsm` | **terminé sans les `.xlsm`** (go d'Alex, D-87) | 94 % (16/17 ; 89 tests Odoo, 300 avec paie + comptabilité ; DAS = Σ ID10 écart 0 ; `.xlsm` à brancher) | `docs/completude/l10n_ga_dgi_edi_4.4.md` |
| 4.5 | `l10n_ga_dgi_edi` | migration des déclarations V1 (ADR-12) | **reportée** (« go pour la 5 sans la 4.5 ») — bloquée par D-07 | — | — |
| C-3 | `l10n_ga_dgi_edi` | complétude du module | à faire | — | — |
| 5 | `l10n_ga_dgi_edi_account` | ID18, ID27, ID23, ID24, ID26 | **terminé** | 96 % (22/23 ; 16 tests du module, 316 avec les 4 modules ; `.xlsm` des annexes à brancher) | `docs/completude/l10n_ga_dgi_edi_account.md` |
| C-4 | `l10n_ga_dgi_edi_account` | complétude du module | **terminé** | 96 % (23/24 ; 8 manques corrigés ; 22 tests du module, 322 avec les 4 modules ; `.xlsm` V1 à brancher) | `docs/completude/l10n_ga_dgi_edi_account_C-4.md` |
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

Voir `docs/decisions/ouvertes.md`. D-04 abandonné par Alex (24/09/2026). Actions attendues d'Alex : D-05 (avant l'étape 6), D-07 (avant l'étape 4.4). Décidés : D-18 à D-22 (2.3), D-23 à D-28 (2.4), D-29 à D-37 (2.5), D-38 à D-46 (2.6), D-47 à D-53 (2.7, go anticipé ; D-47 mentions du bulletin à confirmer), D-54 à D-57 (2.7 b, bulletin au format du modèle), D-58 à D-64 (3, comptabilisation), D-65 à D-73 (4.1, moteur de déclarations, go anticipé), D-74 à D-81 (4.2, ID10 / ID28 / quittances ; D-74 cellule du NIF à confirmer), D-82 à D-86 (4.3, DTS ; D-83 format des portails à confirmer), D-87 à D-94 (4.4, DAS ; D-87 `.xlsm` à brancher, D-90 / D-91 point 09-6 à confirmer), D-95 à D-103 (5, retenues ; D-103 taux 20 / 25 % à confirmer). Dette de 2.5 (régularisation IRPP sans cumuls d'ouverture) soldée par F12.

## Prochaine étape

Au choix d'Alex : étape 6 (`l10n_ga_hr_payroll_migration`, bloquée par D-05 : schéma `hr_payroll_gb`), C-3 (complétude de `l10n_ga_dgi_edi`), ou 4.5 / `.xlsm` dès réception de la V1 (D-07). Démo : `make demo MODULE=l10n_ga_dgi_edi_account` (mise à jour C-4).
