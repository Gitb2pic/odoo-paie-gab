# Avancement — Paie Gabon & déclarations DGI V2

Mis à jour le 24/09/2026 (étape 2.1).

## Étapes

| Étape | Module | Contenu | État | Complétude | Rapport |
|---|---|---|---|---|---|
| Sprint 0 | socle | dépôt, outillage, vérifications Enterprise (14 points) | **terminé** | 100 % | `docs/completude/sprint0.md` |
| 2.1 | `l10n_ga_hr_payroll` | noyau fiscal pur `lib/ga_fiscal_core` | **terminé** — en attente du « go » pour 2.2 | 100 % (334 tests, couverture 100 %, parité oracle ≤ 1 FCFA) | `docs/completude/l10n_ga_hr_payroll_2.1.md` |
| 2.2 | `l10n_ga_hr_payroll` | squelette du module et données | à faire | — | — |
| 2.3 | `l10n_ga_hr_payroll` | modèles, adaptateur et règles liées au noyau | à faire | — | — |
| 2.4 | `l10n_ga_hr_payroll` | conventions, grilles, heures supplémentaires, absences | à faire | — | — |
| 2.5 | `l10n_ga_hr_payroll` | prêts salariés (F1), indemnités récurrentes (F15) | à faire | — | — |
| 2.6 | `l10n_ga_hr_payroll` | import Excel (F3), contrôles avant paie (F8), arrondi espèces (F2), cumuls d'ouverture (F12) | à faire | — | — |
| 2.7 | `l10n_ga_hr_payroll` | rapports : bulletin figé, livre de paie, virements, billetage | à faire | — | — |
| C-1 | `l10n_ga_hr_payroll` | complétude du module (`prompts/99_completude.md`) | à faire | — | — |
| 3 | `l10n_ga_hr_payroll_account` | comptabilisation SYSCOHADA | à faire | — | — |
| C-2 | `l10n_ga_hr_payroll_account` | complétude du module | à faire | — | — |
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

Voir `docs/decisions/ouvertes.md`. À appliquer par Alex : D-04 (`db_name`, `dbfilter`, `list_db` dans `odoo.conf` + redémarrage), puis relancer `make test MODULE=base_setup`. Actions attendues d'Alex : D-05 (schéma `hr_payroll_gb` + lignes fictives, avant l'étape 6), D-07 (copie de la V1, avant l'étape 4.4). Décidés : D-06 (`date_to`), D-08 (ADR acceptés), D-09 (`make demo` sur `odoo19`).

## Prochaine étape

2.2 — squelette du module et données (`prompts/02_l10n_ga_hr_payroll.md`), après le « go » d'Alex. Prérequis conseillé : D-04 appliqué (`odoo.conf`), pour les premiers tests Odoo.
