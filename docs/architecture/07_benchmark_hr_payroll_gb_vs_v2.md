# 07 — Benchmark : `hr_payroll_gb` (freelance) contre l'addon d'Alex (`l10n_ga_dgi_edi` + architecture V2)

Date : 23/09/2026. Code lu dans le dépôt `supergel-compta`, branche `staging` (commit `222c6f6`). Référence fiscale : `base_connaissance/parametres_fiscaux_gabon_2026.yaml` et `calcul_paie_gabon_reference.py`.

## 0. Verdict

| | `hr_payroll_gb` (freelance) | `l10n_ga_dgi_edi` (V1 existante) | Architecture V2 (cible) |
|---|---|---|---|
| Rôle | Paie complète + déclarations CNSS | Déclarations DGI seules, branchées sur `hr_payroll_gb` | Paie + déclarations, sans `hr_payroll_gb` |
| État | En production, **3 défauts bloquants** | Fonctionnelle, 11 fichiers de tests | Sur papier, rien de codé |
| Décision | **Ne pas garder comme socle.** Reprendre les données métier (~20 %) | **Garder ~65 %** (générateurs, classeurs officiels, tests), la découpler | Construire, en y ajoutant 5 fonctions vues chez le freelance (§ 6.3) |

Le calcul IRPP / TCS du freelance est **juste dans sa formule** : une fois les taux 2026 saisis, il donne au franc près les mêmes résultats que le calculateur de référence sur 3 des 4 cas de test (§ 3). Ce qui ne va pas, c'est tout le reste : les assiettes, le net, les absences, les taux sans date et les déclarations.

---

## 1. Ce qui a été analysé

| Source | Volume | Lecture |
|---|---|---|
| `hr_payroll_gb` | 148 règles salariales, 16 fichiers de modèles Python (~5 500 lignes), 11 rapports | règles extraites une par une du XML ; modèles, rapports et sécurité lus |
| `l10n_ga_dgi_edi` | 13 fichiers de modèles, 11 fichiers de tests, 4 classeurs DGI `.xlsm` | modèles clés, carte des rubriques, notes `doc/notes-hr_payroll_gb.md` |
| Architecture V2 | fichiers 00 à 06 du Projet | 01, 05, 06 relus en détail |

Les formules du freelance ont été rejouées en Python et comparées au calculateur de référence (§ 3).

---

## 2. Tableau comparatif

Note sur 5. « — » veut dire hors périmètre. Pour la V2, la note porte sur la conception, pas sur du code.

| Critère | Freelance | `l10n_ga_dgi_edi` | V2 (conception) | Commentaire |
|---|:-:|:-:|:-:|---|
| Conformité 2026 (taux, barème) | 2 | 3 | 5 | Freelance : taux 2025 par défaut (CNSS 2,5 % / 16 %, FNH 2 %). DGI : CFP sans plafond |
| Justesse du calcul | 1 | 3 | 5 | Freelance : net absent pour espèces et chèque, absences non déduites |
| Paramètres datés (changement de loi) | 1 | 1 | 5 | Les deux codes stockent les taux en champs société, sans historique. V2 : `hr.rule.parameter` daté |
| Couverture paie (variables, congés, HS, prêts, pointage) | 4 | — | 3 | Point fort du freelance. V2 n'a encore ni prêts, ni arrondi espèces, ni import des variables |
| Couverture déclarations | 2 | 4 | 4 | Freelance : CNSS mensuelle et trimestrielle, DTS. DGI : ID10, DTS, ID19 à ID26. V2 : ajoute l'ID28, mais repousse ID23/24/26 en V2.0 |
| Intégration Odoo 19 standard | 2 | 3 | 5 | Freelance : redéfinit `wage` et `number`, variables maison hors `hr.payslip.input` |
| Qualité du code | 1 | 3 | 5 | Freelance : doublons, code mort, restes de 4 autres pays |
| Tests automatisés | 0 | 3 | 5 | Freelance : aucun test |
| Multi-société et droits | 1 | 4 | 5 | Freelance : aucun filtre société dans les déclarations, tout au groupe « utilisateur paie » avec suppression |
| Comptabilisation SYSCOHADA | 0 | — | 5 | Freelance : aucune écriture de paie |
| Traçabilité (états, figement) | 1 | 3 | 5 | DGI : `mail.thread` et états. V2 : instantané figé + SHA-256 + rectificative |
| **Total / 55** | **15** | **27 / 45** | **52** | |

---

## 3. Test chiffré sur les 4 cas de référence

Formules du freelance rejouées telles qu'écrites dans `data/hr_payroll_data.xml`, avec deux jeux de taux : ceux par défaut du module, puis les taux 2026 saisis à la main.

| Cas | Rubrique | Référence V2 | Freelance, taux par défaut | Freelance, taux 2026 |
|---|---|--:|--:|--:|
| Ex.1 Célibataire, 545 000 dont transport 30 000 | CNSS salarié | 25 750 | 13 625 | 27 250 |
| | IRPP | 33 500 | 35 252 | 33 181 |
| | Net | 459 002 | 468 199 | 457 326 |
| Ex.2 Marié 2 enfants, 850 000 | Net | 740 547 | 759 120 | **740 547** |
| | Charges patronales | 217 600 | 191 909 | 217 302 |
| Ex.3 Célibataire 1 enfant, 2 000 000 | IRPP | 245 080 | 253 630 | **245 080** |
| | Net | 1 553 170 | 1 580 245 | **1 553 170** |
| Ex.4 Marié 3 enfants, 5 000 000 | Net | 3 793 646 | 3 816 802 | **3 793 646** |
| | Charges patronales | 425 000 | 397 062 | 441 875 |

Ce qu'on en tire :

* **Avec les taux par défaut**, le salarié est surpayé de 9 000 à 27 000 FCFA par mois et les charges patronales sont sous-déclarées de 9 000 à 43 000 FCFA par salarié et par mois. À vérifier en priorité : les taux réellement saisis sur la fiche société en production.
* **Avec les taux 2026**, le net et l'IRPP sont justes au franc pour les cas 2, 3 et 4. Le noyau TCS → IRPP (abattement 20 % plafonné, quotient familial, barème art. 174) est bon.
* **Les écarts qui restent sont structurels** : CFP sans plafond et calculée après cotisations (cas 4 : 24 375 au lieu de 7 500) ; transport soumis à la CNSS (cas 1).
* **Trous dans le barème** : un quotient de 1 920 000,50 donne un IRPP nul (la tranche est testée par `>= 1 920 001`). Au-delà de 99 999 999 de quotient annuel, l'IRPP tombe aussi à zéro.

---

## 4. Défauts du code freelance — ce que la V2 corrige

### 4.1 Bloquants

| # | Défaut | Où | Conséquence | Correction V2 |
|---|---|---|---|---|
| B1 | La règle `NET` est déclarée deux fois avec le même identifiant XML `hr_rule_total_charges_NET`. La seconde (« Virement ») écrase la première (« Espèce ») | `data/hr_payroll_data.xml` l. 2900 et 2916 | Salarié payé en espèces : pas de ligne NET, et la règle `SURPL` (`NET % 500`, l. 2934) plante le calcul. Salarié payé par chèque : pas de net du tout | Une seule règle `NET` standard ; le mode de paiement n'intervient qu'à l'arrondi |
| B2 | Les absences non payées (`ANJ`, `ANH`, `SANC`, `CMD`, catégorie `ABS`) sont calculées mais jamais retirées : `BRUT = BASER + ALW + HS + CNG`. Le salaire mensuel n'est pas proratisé, et les jours de congé (`CNG`) s'ajoutent au salaire plein | l. 1848 (BRUT), l. 288 et suivantes (ABS) | Absence injustifiée payée ; jours de congé payés deux fois pour les mensuels. **À confirmer sur un bulletin test** | Prestations `hr.work.entry` ; le salaire de base suit les jours effectivement rémunérés |
| B3 | Déclarations CNSS : bulletins pris dans tous les états (brouillons et annulés compris), sans filtre société, `limit=1` par code, et code `TALW` qui n'existe dans aucune règle | `models/cnss_mens.py` l. 312 et 350 ; `models/cnss.py` l. 365 | ID10 et DTS fausses dès qu'un bulletin brouillon traîne, en multi-société, ou avec deux bulletins dans le mois. Indemnités toujours à 0 | Lecture `_read_group` des bulletins validés, par société (déjà fait dans `l10n_ga_dgi_edi`) |

### 4.2 Majeurs

| # | Défaut | Où | Correction V2 |
|---|---|---|---|
| M1 | Taux 2025 par défaut (CNSS 2,5 % / 16 %, FNH 2 %) et aucun historique : recalculer un bulletin de 2025 après la mise à jour lui applique les taux 2026 | `models/hr_company.py` l. 20-22 | Paramètres datés `hr.rule.parameter`, générés depuis le YAML |
| M2 | Barème IRPP : trous entre les tranches (tests `>=` / `<=` sur un décimal) et IRPP nul au-delà de 99 999 999 | `data/…` l. 2185 ; `hr_company.py` l. 87 | Barème lu en ordre croissant, borne haute ouverte (`impot_une_part`) |
| M3 | CFP calculée sur le brut **moins** les cotisations salariales, sans plafond de 1 500 000 par salarié | l. 2091 | Base = brut, avantages en nature compris, plafonnée |
| M4 | Assiettes : la catégorie « soumises CNSS » est **entièrement exonérée d'IRPP/TCS**, sans plafond. Elle contient le 13e mois (`P13M`), la gratification, la prime de bilan, l'indemnité de voiture et le transport. Le transport est soumis à la CNSS alors qu'il en est exclu jusqu'à 35 000 | l. 1462 (ITRSP), l. 1788 (P13M) | Deux indicateurs par règle (assiette sociale / assiette fiscale) et plafonds d'exonération paramétrés : gratifications 4 M/an, véhicule 100 000/mois, transport 2 500 / 5 000 par jour |
| M5 | Même code `AIDMED` pour « Aide médicale » et « Prime de lait et poussière ». Avec la règle d'Odoo qui retranche le montant précédent d'un même code, l'aide médicale disparaît du net quand les deux existent | l. 1665 et 2681 | Un code unique par rubrique, vérifié par un test |
| M6 | 23 indemnités définies deux fois, avec le même code dans deux catégories (`INDCNSS` et `INDMNT`). Par la même règle d'Odoo, `INDMNT` retombe à 0, et `TOTAL` (coût employeur), qui lit `INDMNT`, est sous-estimé | seq 81-99 et 1120-1135 | Une règle par rubrique |
| M7 | Avantages en nature : `min(montant saisi, brut) × taux`, calculé sur le brut avant cotisations, sans le plafond nourriture de 120 000. `l10n_ga_dgi_edi` applique ce plafond dans l'ID19 : **le bulletin et la DAS divergent** | l. 1979 | Calcul art. 93 dans le noyau, une seule source pour le bulletin et la DAS |
| M8 | Le champ `wage` de `hr.version` est remplacé par un `related` vers la catégorie : pas de salaire individuel possible, fonctions standard cassées | `models/hr_contract.py` l. 155 | `wage` standard ; minimum conventionnel en contrôle |
| M9 | Le champ `number` du bulletin est remplacé par un calcul non stocké | `models/hr_payslip_ma.py` l. 14 | Numérotation standard |
| M10 | IRPP non retenu s'il est ≤ 1 000 FCFA par mois ; aucune base légale trouvée | l. 2211 | Supprimé, ou paramètre documenté |

### 4.3 Mineurs

* **Code mort et doublons** : modèle `hr.catego` défini 3 fois ; 29 codes de règle en double au total ; `cnss_trim.py` (1 358 lignes), `its.py` et `hr_payment_mode.py` jamais importés.
* **Restes d'autres pays** : NINEA (Sénégal), CMU (Côte d'Ivoire), CIMR / ICE / CIN (Maroc), décret malien et plafond de transport à 25 000 dans les aides à la saisie, rapport `report.hr_payroll_ci…`.
* **Parts fiscales** : un célibataire avec plus de 6 enfants a 5 parts au lieu de 4,5 ; la demi-part « célibataire ayant élevé des enfants » manque. Le bulletin affiche `parts`, qui compte les enfants infirmes deux fois, alors que le calcul utilise `part` : **le bulletin n'affiche pas les parts utilisées pour l'impôt**.
* **Bulletin PDF** : il lit la fiche salarié du jour (parts, avantages, catégorie). Réimprimer un ancien bulletin affiche donc des valeurs fausses. Il plante si la date d'embauche est vide.
* **Variables du mois** : stockées sur `hr.employee` et dans une archive maison, hors `hr.payslip.input` standard. Heures supplémentaires en entier (pas de demi-heure). `AVS` et `ARTN` lisent la fiche et non l'archive. Le verrou de l'archive ne se déclenche jamais.
* **Ancienneté** : 1 % par an à partir de 2 ans, compté en fraction d'année et sans plafond. À caler sur la convention collective.
* **Technique** : aucun arrondi au franc ; `_sql_constraints` (déprécié en 19) ; années 2010-2030 codées en dur ; `env.user.company_id` ; 10 requêtes par salarié dans les déclarations ; aucun test.

---

## 5. Ce qu'on réutilise du freelance

| Élément | Fichier source | Destination V2 | Mode |
|---|---|---|---|
| Nomenclature des ~60 primes et indemnités gabonaises, avec libellés et aides à la saisie | `data/hr_payroll_data.xml`, `employe_monthly_archive.py` | `hr.payslip.input.type` et règles `GA_*` de `l10n_ga_hr_payroll` | **Adapter** : reprendre la liste et les libellés, reclasser chaque rubrique (assiette sociale / fiscale, plafond) |
| Formule TCS → IRPP (abattement, quotient, barème) | règles `BRUTTCS`, `CIMP`, `ABATIR`, `C_IMPDED`, `KIRPP` | tests du noyau `ga_fiscal_core` | **Oracle de recette** : validée au franc (§ 3), à garder pour la paie en parallèle |
| Prêts salariés : échéancier, contrôles (ancienneté ≥ 2 ans, mensualité ≤ 40 %, plafond, dérogation RH), passage à « payé » à la validation du bulletin | `models/hr_employee_loan.py`, `hr_payslip_ma.py` l. 235 | nouveau `l10n_ga.employee.loan` alimentant une entrée `GA_LOAN` | **Reprendre presque tel quel**, renommer, ajouter `company_id` et les droits |
| 12 types de congés et absences gabonais (maladie, naissance, circonstance, maternité, AT, sanction…) | `data/hr_leave_type_data.xml` | `hr.work.entry.type` + `hr.leave.type` Gabon | **Adapter** : même liste, branchée sur les prestations |
| Arrondi des paies en espèces à 500 FCFA avec report du reliquat le mois suivant | règles `SURPL`, `SURPLP`, `NETM`, `NETRM` | option société de `l10n_ga_hr_payroll` | **Idée à reprendre**, réécrite (B1) |
| Mise en page du bulletin : plafonds CNSS/CNAMGS, base TCS, brut imposable, cumuls annuels | `report/report_bulletin_paye.xml`, champs `ytd_*` | `report/report_payslip_ga.xml` | **Inspiration** ; lire les valeurs sur le bulletin, pas sur la fiche |
| Import Excel des variables mensuelles, écran des anomalies salarié | `wizard/import_archive.py`, `views/hr_employee_anomalies_*.xml` | assistant d'import des entrées ; rejoint l'écran « Contrôle DAS » | **Idée** |
| Champs société utiles aux en-têtes DGI/CNSS (n° CNSS, n° CNAMGS, NIF, province, localité, quartier…) | `models/hr_company.py` | `res.company` de `l10n_ga_hr_payroll` | **Reprendre les champs pertinents**, préfixés `l10n_ga_` |

À **ne pas reprendre** : la structure des règles (doublons, catégories), `hr.catego`, la redéfinition de `wage` et `number`, les modèles `hr.cnss*` et le livre de paie maison, les champs d'autres pays.

---

## 6. Ton addon : ce qu'on garde, ce qu'il faut corriger

### 6.1 `l10n_ga_dgi_edi` — à garder pour la V2

* Classeurs officiels DGI `edi-annexe-ID19/21/23/26.xlsm` et leur remplissage (`excel_builder.py`, `excel_tools.py`).
* Générateurs ID19 à ID26 : cadre 3 de l'ID19, contrôle col. 12 = col. 10 de l'ID22, ID24 CEMAC / hors CEMAC. Ils deviennent des « stratégies » du moteur V2.
* Deux quittances par ID10, reprises automatiquement par l'ID22.
* Lecture des bulletins validés par `_read_group`, filtrée par société (le bon modèle, à l'opposé de B3).
* Tâches planifiées (ID10 mensuelle, DTS trimestrielle, annuelles au 15 janvier) et écran « Contrôle DAS ».
* Les 11 fichiers de tests, à porter sur les nouveaux codes de règles.

### 6.2 `l10n_ga_dgi_edi` — à corriger en passant à la V2

| Défaut | Où | Correction |
|---|---|---|
| Dépend de `hr_payroll_gb` et se rattache à `hr.cnss_mens` / `hr.cnss`, dont il hérite les défauts B3 | `__manifest__.py`, `dgi_id10.py` l. 95, `dgi_dts.py` l. 75 | Dépendre de `l10n_ga_hr_payroll` ; supprimer les rattachements |
| CFP de l'ID10 recalculée sur le total (L1 + L2 + L5), sans plafond de 1 500 000 par salarié, et différente de la règle `CFP` de la paie | `dgi_id10.py` l. 390-396 | Une seule source : somme des lignes `GA_CFP` des bulletins |
| Taux (CFP, seuils ID19/ID20, retenue ID24) en champs société non datés | `res_company.py` | Paramètres datés |
| Période lue sur les dates du bulletin (`date_from` / `date_to`) et non sur la date de paiement | `dgi_edi_rule_map.py` | Filtrer sur `l10n_ga_payment_date` : l'ID10 porte sur le mois de paiement |
| Un modèle par déclaration (`dgi.id10`, `dgi.id20`, `dgi.id22`, `dgi.dts`, `dgi.edi.declaration`) | `models/` | Moteur unique `l10n_ga.declaration` + générateurs, instantané figé, empreinte SHA-256, rectificative |
| Carte des rubriques par codes du freelance (`BRUT`, `PCNSS`, `AVTNOURI`…) | `dgi_edi_rule_map.py` | Indicateurs portés par la règle salariale (colonne DAS), codes `GA_*` |
| Fichiers parasites dans le module : `.bak`, `.prev`, `PROMPT-*.md`, dossier `Claude outputs` | racine, `models/`, `report/` | Nettoyer, compléter le `.gitignore` |
| ID28 absent | — | Prévu en V2 |

### 6.3 Architecture V2 — trous révélés par le benchmark

1. **Prêts salariés** : absents de la conception (seules les avances y sont). Ajouter `l10n_ga.employee.loan` (§ 5).
2. **Modes de paiement et arrondi espèces** : absents. Ajouter l'option société.
3. **Import Excel des variables mensuelles** : les clients saisissent aujourd'hui dans une grille. Prévoir un assistant d'import vers `hr.payslip.input`.
4. **ID20, ID22, ID23, ID24, ID26** : déjà codés et testés dans `l10n_ga_dgi_edi`, mais la feuille de route V2 met ID23/24/26 en V2.0 (module comptable). Les porter dès la V1 plutôt que de les perdre pendant plusieurs mois.
5. **Reprise des données** : la migration depuis `hr_payroll_gb` n'est pas prévue (salariés, catégories, prêts en cours, cumuls de l'année pour la régularisation IRPP, archives). Ajouter un script de reprise et une étape de feuille de route.

---

## 7. Plan d'action proposé

| Ordre | Action | Pourquoi maintenant |
|---|---|---|
| 1 | **En production, sans attendre la V2** : vérifier les taux de la fiche société (CNSS 5 % / 18 %, FNH 3 %) et corriger B1 (NET espèces / chèque) | Argent versé et déclaré à tort chaque mois |
| 2 | Produire un bulletin test avec absence et congé pour confirmer B2 | Mesurer le trop-payé |
| 3 | Sprint 0 de la V2 : ajouter les 5 points du § 6.3 à l'architecture | Éviter de découvrir ces manques en recette |
| 4 | Noyau `ga_fiscal_core` + tests, avec les 4 cas de référence et les cas limites du § 3 (trou de barème, plafonds CFP, 13e mois) | Le socle de tout le reste |
| 5 | Porter les générateurs de `l10n_ga_dgi_edi` sur le moteur V2, tests compris | Réutilise ~65 % de l'existant |
| 6 | Recette en parallèle : un mois de paie réelle, V2 contre `hr_payroll_gb` taux 2026 corrigés, écart ≤ 1 FCFA hors défauts listés ici | Critère de sortie V1.0 |

## 8. Points ouverts

* Taux réellement saisis sur la fiche société en production : à relever (conditionne l'ampleur de M1).
* B2 : à confirmer par un bulletin test.
* M5 et M6 reposent sur la façon dont le moteur de paie d'Odoo additionne deux règles de même code (il retranche le montant précédent). Code Enterprise non lu : à confirmer sur un bulletin.
* Prime d'ancienneté : barème de la convention collective du client à obtenir.
* Points 3 à 5 et 13 du fichier `09_points_a_verifier.md` (CNAMGS dans la base TCS, gratifications, logement, transport) : ils décident du reclassement des rubriques du § 5.
