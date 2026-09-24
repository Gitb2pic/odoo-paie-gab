# Mode d'emploi — développer les addons avec Claude Code

## Contenu du dossier

| Fichier | À quoi il sert |
|---|---|
| `CLAUDE.md` | Mémoire permanente de Claude Code : sources, règles d'or, conventions Odoo 19, déroulé d'une session, **protocole de complétude**. À copier à la racine du dépôt. |
| `01_sprint0_socle.md` | Création du dépôt, outillage, lecture du code Enterprise (10 points 🔒). |
| `02_l10n_ga_hr_payroll.md` | Module paie, découpé en 7 étapes (2.1 à 2.7). |
| `03_l10n_ga_hr_payroll_account.md` | Comptabilisation SYSCOHADA. |
| `04_l10n_ga_dgi_edi.md` | Moteur de déclarations, découpé en 5 étapes (4.1 à 4.5). |
| `05_l10n_ga_dgi_edi_account.md` | Retenues fournisseurs et annexes DAS (partie V1.0). |
| `06_l10n_ga_hr_payroll_migration.md` | Module de reprise jetable. |
| `99_completude.md` | Prompt autonome de complétude, à relancer quand tu veux (fin d'étape, fin de module, avant une livraison). |

## Préparation (une seule fois)

1. Avoir sous la main :
   - le code Odoo 19 Community (`$ODOO_PATH`) et **Enterprise** (`$ENTERPRISE_PATH`, indispensable : `hr_payroll` est privé) ;
   - les dossiers `architecture_addon/` et `base_connaissance_fiscale_gabon/` ;
   - les classeurs modèles DGI (ID_10_RASS-CFP.xlsx, CFP_ID28…, Fichier_DAS - v3.xlsx, ID18, ID27) ;
   - si possible le code de la V1 `l10n_ga_dgi_edi` (`$V1_PATH`, pour les gabarits `.xlsm`, les 11 tests et les scripts de migration) et un dump anonymisé contenant les tables `hr_payroll_gb` (pour le module de reprise).
2. Lancer `claude` dans un dossier vide qui deviendra `odoo-ga-payroll/`, puis coller `01_sprint0_socle.md` en remplaçant les chemins entre `<...>`.

## Rythme de travail : une étape = une session

```text
/clear
→ coller le prompt de l'étape (ex. « 02 — étape 2.1 »)
→ Claude lit, propose son plan dans docs/plans/  →  tu relis, tu réponds « go »
→ Claude code en TDD, commit par petits pas
→ Claude exécute le protocole de complétude (C1 à C7) et complète ce qui manque
→ tu lis docs/completude/<module>_<etape>.md
→ étape suivante
```

Règles simples :
- Ne passe pas à l'étape suivante si le rapport de complétude contient un manque non classé « bloquant ».
- Un bloquant = une question pour toi (point Enterprise, décision fiscale, fichier manquant). Réponds-y dans `docs/decisions/ouvertes.md` puis relance `99_completude.md`.
- À la fin de chaque module, lance `99_completude.md` sur **tout le module** (pas seulement la dernière étape).

## Ordre complet

```text
Sprint 0
  └─ 2.1 noyau fiscal → 2.2 données → 2.3 modèles & règles → 2.4 conventions/absences
     → 2.5 prêts & indemnités → 2.6 import, contrôles, arrondi, cumuls → 2.7 rapports
     → complétude module 1
  └─ 3 comptabilisation → complétude module 2
  └─ 4.1 moteur → 4.2 ID10/ID28/quittances → 4.3 DTS → 4.4 DAS → 4.5 migration V1
     → complétude module 3
  └─ 5 retenues ID18/ID27 + ID23/24/26 → complétude module 4
  └─ 6 reprise hr_payroll_gb → complétude module 5
```

Les étapes 4.1 à 4.3 peuvent démarrer dès que l'étape 2.3 est terminée (les déclarations ne lisent que les lignes de bulletins), si tu veux paralléliser.
