# Base de connaissance — Fiscalité & paie Gabon (addon Odoo « Paie et déclarations DGI » V2)

Version : 1.0 — constituée le 23/09/2026 à partir des 32 documents du dossier « addon v2 paie et declaration DGI » et de recherches web (textes officiels et sources professionnelles).
Périmètre : paie (cotisations sociales, impôts et taxes sur salaires), déclarations DGI (ID, CA, CP, TP, DAS) et autres impôts d'entreprise utiles à l'addon.

## Comment utiliser cette base

Chaque fichier traite un thème et contient deux niveaux : la règle fiscale/sociale expliquée (avec sa source), puis un encadré « Pour l'addon » qui traduit la règle en paramètre, règle salariale ou mapping de case.
Chaque règle porte un indice de fiabilité :

| Indice | Signification |
|---|---|
| ✅ Confirmé | Texte officiel (JO, CGI, décret, arrêté) ou au moins deux sources professionnelles concordantes récentes |
| 🟡 Probable | Une source fiable, ou pratique courante non contredite, mais texte primaire non consulté |
| 🔴 À vérifier | Sources contradictoires, texte ambigu, ou valeur issue d'un support pédagogique non fiable |

## Sommaire

| Fichier | Contenu |
|---|---|
| `01_analyse_des_documents_sources.md` | Fiche d'analyse de chacun des 32 documents : nature, date, fiabilité, apports, erreurs détectées |
| `02_cadre_legal_et_calendrier.md` | Textes applicables en 2026 (CGI, LF 2026, LFR 2026, Code du travail, Code de sécurité sociale) et calendrier déclaratif complet |
| `03_cotisations_sociales_CNSS_CNAMGS.md` | Taux 2026, plafonds, assiette (arrêté 016/MTEPS), exclusions, DTS, pénalités, prestations |
| `04_impots_sur_salaires_IRPP_TCS_FNH_CFP.md` | IRPP (barème, quotient familial, abattement), TCS, FNH, CFP, avantages en nature, algorithme pas-à-pas + exemples vérifiés |
| `05_elements_de_remuneration.md` | Matrice primes/indemnités (fiscal / social / congés), heures sup, congés payés, ancienneté, ruptures, saisies |
| `06_declarations_salaires_ID10_ID28_DAS.md` | Mapping case par case de l'ID10, ID28 et de la DAS (ID19 à ID26), anomalies des modèles Excel |
| `07_autres_impots_entreprise.md` | IS/IMF/acomptes, TVA/CSS, retenues à la source (ID09, ID18, ID27, ID31), patente, CFU, facturation électronique |
| `08_specifications_addon_odoo.md` | Spécifications fonctionnelles et techniques pour l'addon (paramètres datés, règles, champs, génération Excel/PDF, contrôles) |
| `09_points_a_verifier.md` | Contradictions, ambiguïtés et questions à trancher avec la DGI / un fiscaliste |
| `parametres_fiscaux_gabon_2026.yaml` | Tous les taux, plafonds et barèmes en format machine (à charger dans l'addon) |
| `calcul_paie_gabon_reference.py` | Calculateur de référence (Python) avec tests — sert d'oracle pour les tests unitaires de l'addon |

## Les 10 chiffres à retenir (paie 2026)

| Élément | Valeur 2026 | Fiabilité |
|---|---|---|
| CNSS salarié / employeur | 5 % / 18 % (PF 5 + AT 2 + AVID 11), plafond 1 500 000 FCFA/mois | ✅ |
| CNAMGS salarié / employeur | 2 % / 4,1 %, plafond 2 500 000 FCFA/mois | ✅ |
| TCS | 5 % de la fraction mensuelle > 150 000 FCFA (après cotisations sociales salariales) | ✅ taux et seuil / 🟡 déduction CNAMGS |
| IRPP | Barème art. 174 (0 % à 35 %) sur quotient familial annuel, abattement 20 % plafonné à 10 000 000 FCFA/an | ✅ |
| FNH | 3 % employeur (LFR 2026, loi 002/2026) sur assiette CNSS plafonnée — auparavant 2 % | ✅ taux / 🔴 date d'effet et répartition |
| CFP | 0,5 % employeur sur la masse salariale brute plafonnée 1 500 000/mois | ✅ |
| SMIG / RMM | 80 000 FCFA / 150 000 FCFA | ✅ |
| Déclaration ID10 (IRPP+TCS+FNH+CFP) | le 15 du mois suivant le paiement | ✅ |
| DTS CNSS / CNAMGS | trimestrielle, dans les 30 jours suivant le trimestre | ✅ |
| DAS (ID19 à ID26) | au plus tard le 30 avril N+1 (art. 167 ter CGI) | ✅ |

## Changements majeurs 2026 à intégrer dans l'addon

La réforme CNSS (décret n°0487/PR/MASI du 18/12/2025) double la part salariale (2,5 % → 5 %) et restructure la part patronale (16 % → 18 %). La LF 2026 (loi n°041/2025 du 29/12/2025) remplace la CFPB/CFPNB par la Contribution Foncière Unique, refond la patente (0,1 % du CA), impose la facture électronique normalisée et porte temporairement le précompte sur loyers à 10 %. La LFR 2026 (loi n°002/2026, promulguée le 17/07/2026) porte le FNH à 3 %, ramène le précompte loyers à 5 %, fixe l'exonération de l'indemnité de voiture à 100 000 FCFA/mois et modifie la TVA.
Les modèles Excel TP01, TP02 et CP04 du dossier sont donc obsolètes pour 2026, et le taux FNH à 2 % des anciens supports aussi.
