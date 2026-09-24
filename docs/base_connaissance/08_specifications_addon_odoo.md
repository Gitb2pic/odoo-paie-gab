# 08 — Spécifications pour l'addon Odoo (paie Gabon + déclarations DGI)

Rappel des exigences posées pour l'addon : intégration native à la paie et à la comptabilité Odoo, données lues dans Odoo, **aucune génération XML** (sorties Excel et PDF uniquement), génération automatique des imprimés sans ressaisie, simplicité d'usage. La V2 ajoute notamment l'ID01 (et l'ID14).

## 1. Principes d'architecture

1. **Aucun taux en dur.** Tous les taux, plafonds, seuils et barèmes sont des paramètres datés (`hr.rule.parameter` / `hr.rule.parameter.value` avec `date_from`), chargés depuis `parametres_fiscaux_gabon_2026.yaml`. Justification : 2026 a connu trois changements en cours d'année (réforme CNSS au 01/01, LF 2026, LFR 2026 en juillet) et plusieurs dates d'effet restent incertaines.
2. **Chaque rubrique porte sa fiscalité** : indicateurs soumis CNSS / CNAMGS / IRPP-TCS / CFP / FNH / congés / rupture, et plafond d'exonération éventuel (fichier 05). Les règles d'assiette additionnent les rubriques par indicateur au lieu de lister des codes.
3. **Déclarations = agrégats de bulletins validés**, filtrés par **date de paiement** (ID10) ou par année civile (DAS), jamais par saisie.
4. **Traçabilité** : chaque montant d'une déclaration doit pouvoir être expliqué par un rapport de détail (salarié × rubrique) exportable en Excel.
5. **Multi-société** : paramètres société (NIF, code résidence, n° CNSS employeur, centre des impôts, mode ID10 ou ID10 + ID28, répartition FNH).

## 2. Données de référence à ajouter

### Société (`res.company`)

NIF ; numéro statistique ; RCCM ; n° d'affiliation CNSS ; n° CNAMGS ; centre des impôts et code résidence ; régime (DGE / CIME / autre, pour le mode de paiement) ; convention collective ; option CFP (ID10 ou ID28) ; taux AT spécifique éventuel.

### Salarié (`hr.employee`)

Matricule ; n° CNSS ; n° CNAMGS ; NIF ; nationalité (code DAS 1 à 4 calculé) ; situation familiale (marié, célibataire, veuf, divorcé) ; nombre d'enfants à charge et d'enfants infirmes ; indicateur « parts majorées 1,5 » ; **nombre de parts calculé** (fichier 04 §1.3) avec possibilité de forçage motivé ; code emploi et code niveau DGI ; catégorie conventionnelle ; mode de transport (2 ou 4 trajets/jour) ; véhicule de fonction (oui/non) ; date d'embauche (ancienneté).

### Contrat (Odoo 18 `hr.contract` / Odoo 19 `hr.version`)

Salaire de base conventionnel, sursalaire, régime horaire (40 h), avantages en nature fournis (logement, domesticité, eau/électricité, nourriture, arrêté 259 oui/non), indemnités contractuelles.

## 3. Catégories et règles salariales (structure « Gabon — Employé »)

| Ordre | Code | Calcul |
|---|---|---|
| 1 | Gains | BASE, SURSAL, HS (table conventionnelle), ANC (auto selon ancienneté), primes, indemnités, AN valorisés |
| 10 | `BRUT` | Σ gains |
| 20 | `ASSIETTE_SOC` | Σ gains soumis + excédent transport/véhicule/carburant au-delà de 35 000 ; min SMIG au prorata |
| 21 | `CNSS_SAL` / `CNAMGS_SAL` | 5 % × min(assiette, 1,5 M) / 2 % × min(assiette, 2,5 M) |
| 30 | `BRUT_IMP` | Σ gains soumis à l'IRPP ; gratifications exonérées dans la limite du cumul annuel 4 M (compteur annuel) ; indemnités 91 bis dans leurs plafonds (100 000 véhicule, 2 500/5 000 transport × jours de présence, 20 000 × enfants) |
| 31 | `BASE_TCS` / `TCS` | BRUT_IMP − cotisations salariales ; 5 % × max(0, base − 150 000) |
| 32 | `IRPP` | annualisation, abattement 20 % plafonné 10 M, quotient, barème × parts / 12 |
| 33 | `REGUL_IRPP` | en décembre ou au départ : IRPP recalculé sur le cumul annuel − cumul retenu |
| 40 | Retenues diverses | avances, prêts, cessions, saisies (contrôle de la quotité saisissable) |
| 50 | `NET` | BRUT − retenues + gains non soumis |
| 60 | Charges patronales | `CNSS_PF` 5 %, `CNSS_AT` 2 %, `CNSS_AVID` 11 %, `CNAMGS_PAT` 4,1 %, `FNH` 3 %, `CFP` 0,5 % |
| 70 | `COUT` | BRUT + charges patronales |

Tests : reprendre les 4 exemples du fichier 04 §8 comme tests unitaires (`calcul_paie_gabon_reference.py` sert d'oracle).

## 4. Déclarations à générer (Excel + PDF)

| Imprimé | Période | Données | Priorité |
|---|---|---|---|
| ID10 | mensuelle (date de paiement) | Σ IRPP, TCS, FNH ; cadre CFP (L1 à L7) | V1 ✅ |
| ID28 | mensuelle | CFP si option séparée | V1 |
| DTS CNSS / DTS CNAMGS | trimestrielle | état nominatif par salarié, 3 mois, cotisations | V1 (état de préparation, dépôt sur les portails) |
| DAS : ID19, ID20, ID21, ID22 | annuelle (au 30 avril N+1) | fichier 06 §3 | V1 ✅ |
| DAS : ID23, ID24, ID26 | annuelle | factures fournisseurs (honoraires, non-résidents, prestataires non TVA) | V1 (lien comptabilité) |
| ID18, ID27 | mensuelle | retenues 9,5 % / 20 % sur factures fournisseurs | V2 |
| ID30 / CA01 | mensuelle (le 20) | CSS 1 %, TVA via grilles de taxes | V2 |
| ID01, ID02, ID03 | annuelle / acomptes | IS, IMF, acomptes | V2 |
| ID09, ID31 | mensuelle / trimestrielle | loyers | V2 |

Format : modèle Excel fidèle à l'imprimé DGI (mêmes libellés et cases) rempli par `openpyxl`/`xlsxwriter`, et PDF QWeb de même mise en page. Les valeurs sont écrites en dur (pas de formules) pour éviter les anomalies des modèles actuels.

## 5. Comptabilisation (SYSCOHADA)

| Écriture | Débit | Crédit |
|---|---|---|
| Salaires bruts | 661 (rémunérations du personnel national) / 662 (non national) / 663 (indemnités) | 422 Personnel, rémunérations dues |
| Retenues salariales | 422 | 431 CNSS (part salariale), 431x CNAMGS, 447 État impôts retenus (IRPP, TCS) |
| Charges patronales | 664 Charges sociales ; 6413 taxes sur appointements et salaires (FNH), 6415 formation professionnelle (CFP) | 431, 431x, 447 |
| Paiement | 422 | 521 banque / 571 caisse |
| Déclarations | 431 / 447 | 521 |

Le plan de comptes exact doit être paramétrable par rubrique (compte débit/crédit) ; le rapprochement 447 ↔ ID10 et 431 ↔ DTS fait partie des contrôles.

## 6. Contrôles bloquants avant validation d'une déclaration

- Salarié sans n° CNSS, sans NIF (si exigé), sans situation familiale ou sans nombre d'enfants.
- Nombre de parts hors bornes (1 à 5,5 avec infirmes) ou incohérent avec la situation.
- Bulletin sous le SMIG sans motif (temps partiel, absence).
- Écart entre cumuls des bulletins et déclaration (arrondis compris) ; déclaration déjà déposée pour la même période.
- Paramètre manquant à la date de paie (ex. taux FNH non défini).

## 7. Points de conception à trancher avec le client

1. Répartition du FNH 3 % (100 % employeur par défaut) et date de première application.
2. Méthode IRPP : mensuelle simple ou mensuelle avec régularisation annuelle automatique.
3. Application stricte de l'exonération de 4 000 000 sur les gratifications (compteur annuel par salarié).
4. Règle de l'indemnité de logement (fichier 09, point 5).
5. Taux d'heures supplémentaires de la convention collective du client.
6. Dépôt CFP via ID10 ou ID28.
7. Remplacement des modèles obsolètes (CP04, TP01, TP02) par les nouveaux imprimés patente et CFU si la V2 les couvre.
