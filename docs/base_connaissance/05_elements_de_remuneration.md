# 05 — Éléments de rémunération : matrice de traitement et règles de calcul

## 1. Matrice des rubriques (catalogue pour l'addon)

Lecture : **Social** = soumis CNSS/CNAMGS (arrêté 016/MTEPS) ; **Fiscal** = soumis IRPP et TCS ; **Congés** = inclus dans la base de l'allocation de congé ; **Rupture** = inclus dans le salaire de référence des indemnités de préavis, licenciement, ISR.
O = oui, N = non, P = oui au-delà d'un plafond, C = conditionnel.

| Code proposé | Rubrique | Social | Fiscal | Congés | Rupture | Commentaire / source |
|---|---|---|---|---|---|---|
| BASE | Salaire de base | O | O | O | O | art. 169 CT |
| SURSAL | Sursalaire (majoration individuelle) | O | O | O | O | — |
| HS | Heures supplémentaires | O | O | O | O (moyenne) | taux conventionnels (§3) |
| ANC | Prime d'ancienneté | O | O | O | O | 2 % après 2 ans, +1 %/an (tronc commun) |
| ASSID | Prime d'assiduité | O | O | C | O | art. 225 CT : peut être exclue de l'allocation de congé |
| REND | Prime de rendement / performance | O | P (cumul gratifications > 4 M/an) | C | O | instruction 144/2004 🟡 |
| 13M | 13e mois, prime de fin d'année, bonus, bilan, résultat, intéressement | O | P (cumul > 4 M/an) | N (sauf usage) | N (sauf usage) | idem |
| RESP | Indemnité de responsabilité | O | N (si justifiée) | O | O | art. 91 bis — cotisable (arrêté 016 art. 2) |
| CAISSE | Prime / indemnité de caisse | N | N (si responsable de caisse) | N | N | art. 91 bis ; arrêté 016 art. 3 |
| REPR | Indemnité de représentation | O | N (si justifiée) | N | N | art. 91 bis ; cotisable selon arrêté 016 |
| FONCT | Indemnité de fonction | O | O | O | O | — |
| NUIT | Prime de nuit (21h-6h) | O | O | C | O | conventions |
| QUART | Prime de quart / feu continu | O | O | C | O | ex. pétrole : 25,5 % (3×8), 8 % (2×8), 30 % (4×8) du salaire catégoriel |
| INTERIM | Prime d'intérim | O | O | O | O | 50 % de l'écart, 100 % après le délai |
| EXPAT | Indemnité d'expatriation / éloignement / brousse | O | O | C | O | — |
| RISQUE | Primes de risque, pénibilité, technicité, sujétion, diplôme, vie chère | O | O | C | O | arrêté 016 art. 2 |
| LOGT_ESP | Indemnité de logement (espèces) | O | C (voir fichier 04 §5) | O | O | 🔴 règle 250 000 / 40 % / 6 % |
| AN_LOGT | Avantage en nature logement | O (6 %) | O (6 %) | — | O | art. 93 |
| AN_DOM | Avantage domesticité | O (5 %) | O (5 %) | — | O | art. 93 |
| AN_EAU | Avantage eau / électricité | O (5 %) | O (5 %) | — | O | art. 93 |
| AN_NOUR | Avantage nourriture | O (25 %, max 120 000) | O (idem, sauf arrêté 259) | — | O | art. 93 |
| TRANSP | Indemnité de transport | P (cumul > 35 000 avec véhicule/carburant/km) | P (> 2 500 ou 5 000 par jour) | N | N | décret 0126/2010 : minimum 35 000/mois |
| VEHIC | Indemnité de voiture / entretien véhicule | P (cumul 35 000) | P (> 100 000/mois) | N | N | art. 91 bis al. 5 (LFR 2026) |
| CARBU | Indemnité de carburant / kilométrique | P (cumul 35 000) | 🔴 non listée à l'art. 91 bis : imposable par défaut | N | N | — |
| DEPL | Indemnité de déplacement / mission / voyage | N | N (si exacte) | N | N | art. 172 CT, art. 48 tronc commun |
| PANIER | Prime de panier / repas | N | 🔴 non listée art. 91 bis | N | N | arrêté 016 art. 3 |
| SALISS | Primes de salissure, vestimentaire, blanchissage, coiffure, beauté | N | N (vêtement : tenues professionnelles) | N | N | — |
| FAMIL | Primes familiales (trousseau, scolarité, jardin, transport d'enfants) | N (frais de scolarité) | P (> 20 000 par enfant et par mois) | N | N | art. 91 |
| SOLID | Prime de solidarité | N | 🔴 | N | N | décret 128/2010 |
| CONGE | Allocation de congés payés | O | O | — | O | — |
| ICCP | Indemnité compensatrice de congés payés (rupture) | O | O | — | — | — |
| PREAV | Indemnité compensatrice de préavis | O | O | — | — | art. 86 CT |
| LICENC | Indemnité de licenciement | O | N | — | — | fiscal : art. 91 ter 🟡 |
| ISR_RET | Indemnité de services rendus — retraite / décès | O (50 %) | O (50 %) | — | — | NC 000134/2004 |
| ISR_DEM | ISR — démission | O (100 %) | O (100 %) | — | — | — |
| ISR_PS | ISR — départ volontaire (plan social) | N | N | — | — | arrêté 016 art. 3 |
| COMPL_IJ | Complément employeur aux IJ maladie/maternité/AT | O | O | — | — | arrêté 016 art. 2 |
| JETONS | Jetons de présence | N | O (revenu non salarial, ID23) | N | N | — |
| REGUL_IRPP | Régularisation / remboursement IRPP | — | (négatif) | — | — | gain positif en cas de trop-perçu |

## 2. Temps de travail et taux horaire

- Durée légale : 40 heures par semaine ; mois de référence = **173,33 heures** ((40 × 52) / 12) ou 20 jours (arrêté 016, art. 5). ✅
- Taux horaire = salaire mensuel de base / 173,33.
- Retenue pour absence ou retard : strictement proportionnelle au temps non travaillé (les amendes et sanctions pécuniaires sont interdites). ✅
- Travail de nuit : entre 21 h et 6 h (8 heures consécutives maximum). ✅

## 3. Heures supplémentaires 🔴

Formule : `HS = (salaire mensuel / 173,33) × heures × (1 + majoration)`.
Les taux de majoration sont fixés par décret et par les conventions collectives (art. 156 CT : les conventions « comprennent obligatoirement » les majorations). Les sources consultées se contredisent (exemples : +10 %/+25 %/+50 %/+100 %, ou +25 %/+50 %/+60 %/+100 %) et aucune ne cite le décret en vigueur. Le document C241 rappelle qu'en l'absence de convention ou d'accord, aucune majoration n'est imposée par le Code.
**Pour l'addon : ne pas coder de taux en dur.** Créer une table paramétrable par convention collective (tranche horaire, jour/nuit, dimanche, jour férié, taux) et proposer par défaut les taux de la convention de l'entreprise (à obtenir du client).

## 4. Prime d'ancienneté (tronc commun des conventions collectives) 🟡

2 % du salaire de base conventionnel après 2 ans de présence, puis +1 % par année supplémentaire (soit 2 % à 2 ans, 3 % à 3 ans...), plafond selon la convention. Les absences régulières suspendent l'acquisition sans la supprimer ; congés payés et exceptionnels ne l'interrompent pas. Mention distincte obligatoire sur le bulletin.
Exemple de grille (convention Commerce, support 2012, à actualiser) : catégorie 1 = 105 000 ; cat. 7 = 153 500 ; AM1 = 194 600 ; C1 = 295 400 ; C4 = 592 600 FCFA/mois.

## 5. Congés payés ✅

- Acquisition : 2 jours ouvrables par mois de service effectif (24 jours/an) ; 2,5 jours pour les moins de 18 ans (30 jours) ; +1 jour par an par enfant à charge de moins de 16 ans pour les mères de famille (art. 186) ; congés supplémentaires d'ancienneté selon convention.
- Allocation de congé (circulaire n°565) : adultes = 1/12 de la rémunération de la période de référence ; moins de 18 ans = 5/48. Elle ne peut être inférieure au salaire que le salarié aurait perçu s'il avait travaillé (règle du plus favorable).
- Chaque jour de congé supplémentaire = allocation principale / nombre de jours ouvrables du congé principal.
- Exclusions possibles de la base (art. 225 CT) : primes de rendement ou d'assiduité, indemnités de risques, indemnités de frais autres que le logement ; gratifications annuelles exclues sauf usage.
- Indemnité compensatrice en lieu et place du congé : interdite sauf rupture du contrat.

## 6. Rupture du contrat

- **Préavis** : durée selon ancienneté, catégorie et convention ; indemnité compensatrice = rémunération et avantages de toute nature dont le salarié aurait bénéficié (art. 86 CT), calculée sur la moyenne des 12 derniers mois (hors éléments exclus). Exemple ULYSS : 4 ans 5 mois, cadre → 2 mois.
- **Indemnité de licenciement / ISR** : 20 % du salaire moyen mensuel des 12 derniers mois par année de présence (art. 73 ancien CT), avec prorata des mois ; conventions plus favorables (commerce : 20 % de 0 à 5 ans, 25 % de 5 à 10, 30 % de 10 à 15, 35 % au-delà). Salaire global = rémunération brute y compris primes et indemnités (circulaire du 17/10/1981). ISR due en cas de retraite ou de décès après 2 ans ; en cas de démission seulement après 5 ans et faute de l'employeur reconnue par le tribunal (loi 12/2000).
- **Solde de tout compte** : ICCP + préavis + indemnités + prorata du 13e mois selon la convention + régularisation IRPP de l'année.

## 7. Minimums et retenues

- SMIG : 80 000 FCFA/mois (inchangé en 2026) ; RMM : 150 000 FCFA/mois ; indemnité de transport minimale : 35 000 FCFA/mois. ✅
- Retenues autorisées : cotisations et impôts, avances et acomptes, cessions volontaires, saisies judiciaires ; retenues interdites : amendes.
- **Quotité cessible ou saisissable** (art. 729 CPC, barème 2012 🟡 à actualiser) : 5 % jusqu'à 25 000 ; 10 % de 25 000 à 50 000 ; 20 % de 50 000 à 75 000 ; 25 % de 75 000 à 100 000 ; 30 % de 100 000 à 150 000 ; 100 % au-delà de 150 000. Exemple : salaire 160 000 → 40 000 FCFA maximum.
