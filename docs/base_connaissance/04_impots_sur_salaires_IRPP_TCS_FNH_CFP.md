# 04 — Impôts et taxes sur salaires : IRPP, TCS, FNH, CFP

Quatre prélèvements fiscaux touchent la paie. Deux sont retenus sur le salarié (IRPP et TCS), deux sont à la charge de l'employeur (FNH et CFP). Tous sont déclarés et payés le 15 du mois suivant le paiement des salaires sur l'imprimé ID10 (la CFP peut aussi passer par l'ID28).

## 1. IRPP — impôt sur le revenu des personnes physiques (retenue à la source)

### 1.1 Revenu imposable

Revenu brut imposable (RBI) = rémunération en espèces (salaire de base, heures sup, primes et indemnités imposables) + avantages en nature évalués (art. 93) − éléments exonérés (art. 91, 91 bis, 91 ter, instruction 144/2004).
Du RBI on déduit les cotisations sociales salariales (CNSS, CNAMGS, retraites complémentaires obligatoires) puis la TCS retenue (le bulletin ID19 prévoit la ligne « à déduire : taxe complémentaire retenue pour l'année »). ✅
On applique ensuite l'abattement forfaitaire pour frais professionnels de **20 %, plafonné à 10 000 000 FCFA par an et par salarié** ✅ (soit 833 333 FCFA/mois : l'abattement est plein jusqu'à 4 166 666 FCFA de base mensuelle).
Le revenu net imposable (RNI) annuel est divisé par le nombre de parts pour obtenir le quotient familial Q.

### 1.2 Barème (art. 174 CGI, LF 2010 — toujours en vigueur en 2026) ✅

Source : CGI art. 174 (LF 2010, reproduit dans le support ULYSS), PwC Worldwide Tax Summaries Gabon (revue du 06/08/2026). Continuité des constantes vérifiée par calcul.

| Quotient familial annuel Q (1 part) | Taux | Impôt pour 1 part |
|---|---|---|
| 0 – 1 500 000 | 0 % | 0 |
| 1 500 001 – 1 920 000 | 5 % | 5 % × Q − 75 000 |
| 1 920 001 – 2 700 000 | 10 % | 10 % × Q − 171 000 |
| 2 700 001 – 3 600 000 | 15 % | 15 % × Q − 306 000 |
| 3 600 001 – 5 160 000 | 20 % | 20 % × Q − 486 000 |
| 5 160 001 – 7 500 000 | 25 % | 25 % × Q − 744 000 |
| 7 500 001 – 11 000 000 | 30 % | 30 % × Q − 1 119 000 |
| au-delà de 11 000 000 | 35 % | 35 % × Q − 1 669 000 |

IRPP annuel = impôt pour 1 part × nombre de parts ; IRPP mensuel = IRPP annuel / 12.
Le barème « 0 / 8 / 15 / 28 / 40 % » du document `BAREME-IRPP.pdf` n'est pas le barème gabonais (voir fichier 01, A8).

### 1.3 Quotient familial — nombre de parts (art. 170-173) ✅

| Situation | Parts |
|---|---|
| Célibataire, divorcé ou veuf sans enfant à charge | 1 |
| Célibataire, divorcé ou veuf sans enfant à charge ayant élevé des enfants majeurs ou perdu un enfant de 16 ans ou plus, ou titulaire d'une pension d'invalidité ≥ 40 % ou de guerre | 1,5 |
| Marié sans enfant ; célibataire ou divorcé avec 1 enfant | 2 |
| Marié (ou veuf) avec 1 enfant ; célibataire ou divorcé avec 2 enfants | 2,5 |
| Marié (ou veuf) avec 2 enfants ; célibataire ou divorcé avec 3 enfants | 3 |
| Marié (ou veuf) avec 3 enfants ; célibataire ou divorcé avec 4 enfants | 3,5 |
| Et ainsi de suite : + 0,5 par enfant | |

Règles : 6 enfants maximum pris en compte (plafond : 5 parts marié, 4,5 parts célibataire) ; enfant infirme = 1 part au lieu de 0,5 ; le veuf avec enfants est traité comme un marié (le texte cite « dans les 2 ans du décès » : 🟡).
Formules : marié ou veuf avec enfants → `2 + 0,5 × n` ; célibataire/divorcé → `1` si n = 0, sinon `2 + 0,5 × (n − 1)`.

### 1.4 Charges déductibles du revenu global (déclaration annuelle du salarié, pas la paie mensuelle)

Intérêts d'emprunt pour la résidence principale au Gabon (max 6 000 000/an), pensions alimentaires fixées en justice, cotisations de retraite volontaire (max 10 % du revenu brut global), primes d'assurance-vie (max 5 % du revenu brut imposable). 🟡 Ces déductions relèvent de la déclaration ID06 du salarié ; l'addon peut les ignorer en paie.

## 2. TCS — taxe complémentaire sur les traitements et salaires (TCTS) ✅

| Élément | Règle |
|---|---|
| Redevable | Le salarié (retenue par l'employeur) |
| Base | Salaire brut imposable − cotisations sociales salariales |
| Fraction exonérée | 150 000 FCFA par mois (100 000 avant la LF qui l'a relevée ; ex-art. 347) |
| Taux | 5 % |
| Formule | `TCS = 5 % × max(0, base − 150 000)` |
| Déductibilité | La TCS retenue est déduite de la base IRPP |
| Exonérations | Mêmes primes et indemnités exonérées que pour l'IRPP (art. 91 bis, gratifications ≤ 4 M, indemnité de licenciement...) |

Sources : PwC (revue 2026) « XAF 150 000 per month is exempted », calendrier fiscal Business Consulting Gabon (« 5 % après déduction de 150 000 »), support ULYSS 2012 (base = brut − CNSS).
🟡 La déduction de la part salariale CNAMGS dans la base TCS n'est explicitée par aucun texte consulté (la CNAMGS salariale est postérieure à l'ancien art. 347) ; la pratique des logiciels l'inclut (« cotisations salariales »). Paramètre `tcs_deduit_cnamgs` = vrai par défaut.

## 3. FNH — Fonds national de l'habitat ✅ (taux) / 🔴 (répartition, date d'effet)

LFR 2026 (loi n°002/2026, décret de promulgation n°0322/PR du 17/07/2026), nouveaux articles 401 à 404 bis du CGI :

- **Assiette** (art. 401) : l'ensemble des salaires, avantages et indemnités constituant l'assiette des cotisations prestations familiales et accidents du travail, **dans la limite du plafond CNSS** (1 500 000/mois).
- **Redevables** (art. 402) : employeurs du secteur public (sauf l'État) et du secteur privé assujettis au régime CNSS.
- **Taux** (art. 403) : **3 %** (auparavant 2 % de la base CNSS).
- **Déclaration et paiement** (art. 404) : mêmes modalités que les retenues à la source sur salaires (art. 95-96), donc ligne FNH de l'ID10, le 15 du mois suivant.
- **Sanctions** (art. 404 bis) : art. P-996 et suivants.

Points ouverts : la loi ne précise pas si une part peut être répercutée sur le salarié (Gabonreview, 26/07/2026) ; date de première application (paie de juillet ou d'août 2026 ?) à confirmer. L'addon doit prévoir une répartition paramétrable (par défaut 100 % employeur).

## 4. CFP — Contribution à la formation professionnelle ✅

LF 2017, articles 5 à 12 (textes fiscaux non codifiés) :

- **Redevables** : sociétés et personnes morales soumises à l'IS ; personnes physiques relevant des BIC et BNC (art. 6).
- **Base** (art. 8) : masse salariale = rémunération brute mensuelle de chaque salarié, y compris indemnités, primes, gratifications et avantages en argent et en nature, **avant déduction** des retenues pour pensions et sécurité sociale, **dans la limite du plafond** fixé par les textes de protection sociale (1 500 000/mois).
- **Taux** : 0,5 % (art. 9) ; précompte mensuel, reversement à la recette des impôts (art. 10) ; régime de contrôle et sanctions de l'IRPP (art. 11).
- Imprimés : ID10 cadre 3 (lignes 1 à 7) ou ID28. Les deux modèles diffèrent sur le calcul des avantages en nature (fichier 06).

## 5. Avantages en nature (art. 93 CGI) ✅

| Avantage | Évaluation forfaitaire | Base |
|---|---|---|
| Logement | 6 % | du salaire brut diminué des cotisations sociales (CNSS, retraite) |
| Domesticité (gens de maison) | 5 % | idem |
| Eau et électricité (éclairage) | 5 % | idem |
| Nourriture | 25 % | de la rémunération principale, plafonné à 120 000 FCFA par personne et par mois |
| Véhicule | non prévu par l'art. 93 dans les sources consultées | 🔴 à vérifier |

- Si le salarié rembourse à l'employeur la valeur exacte de l'avantage, il n'est pas imposable (art. 93 al. 4).
- Nourriture fournie dans le cadre de l'arrêté n°259 (chantiers, zones isolées) : non imposable ; hors de ce cadre (centres urbains) : 25 % plafonné à 120 000.
- **Indemnité de logement versée en espèces** : la fraction qui dépasse 250 000 FCFA ou 40 % du salaire brut mensuel (avant cette indemnité) est imposable en totalité. 🔴 La lecture du seuil (le plus faible ou le plus élevé des deux ?) et l'articulation avec le forfait de 6 % sont ambiguës dans les sources ; voir fichier 09. Les mêmes taux servent à valoriser les avantages dans l'assiette CNSS (arrêté 016).

## 6. Primes et indemnités exonérées (IRPP et TCS)

| Élément | Régime fiscal | Condition / plafond | Source |
|---|---|---|---|
| Prime de caisse, indemnités de responsabilité, de représentation, de mission, de vêtement, de déplacement | Exonérées (remboursement de frais) | Liste limitative ; frais réels, non exagérés, utilisés conformément | art. 91 bis ✅ |
| Indemnité de voiture / entretien de véhicule | Exonérée | ≤ 100 000 FCFA/mois, sans véhicule de fonction, usage professionnel | art. 91 bis al. 5 (LFR 2026) ✅ |
| Indemnité de transport domicile-travail | Exonérée | 2 500 FCFA/jour (2 trajets) ou 5 000 FCFA/jour (4 trajets) ; réintégrée si l'entreprise transporte ou loge le salarié | art. 91 bis 🟡 |
| Allocations familiales, primes à caractère familial (trousseau, scolarité, jardin d'enfants, transport d'enfants, séparation) | Exonérées | ≤ 20 000 FCFA par enfant et par mois | art. 91 🟡 |
| Gratifications (13e mois, fin d'année, bonus, performance, rendement, intéressement, résultat) | Exonérées | Limite annuelle globale 4 000 000 FCFA par salarié ; au-delà imposables | instruction 144/2004 🟡 |
| Indemnité de licenciement | Exonérée d'IRPP et TCS | Dans la limite légale ou conventionnelle 🔴 | art. 91 ter 🟡 |
| ISR (services rendus) | Imposable à 50 % (retraite, décès), 100 % (démission), exonérée (départ volontaire plan social) | — | NC 000134/2004 🟡 |
| Indemnité compensatrice de préavis, de congés payés | Imposables | — | ✅ |
| Prestations CNSS (IJ, allocations) | Non imposables | — | ✅ |

## 7. Algorithme de calcul mensuel (à coder dans l'addon)

1. `GAINS` = somme des rubriques de gains du mois (y compris avantages en nature valorisés).
2. `ASSIETTE_SOC` = `GAINS` − rubriques exclues de l'assiette sociale (y compris la part de transport/véhicule/carburant ≤ 35 000) ; minimum SMIG.
3. `CNSS_SAL` = 5 % × min(`ASSIETTE_SOC`, 1 500 000) ; `CNAMGS_SAL` = 2 % × min(`ASSIETTE_SOC`, 2 500 000).
4. `BRUT_IMPOSABLE` = `GAINS` − rubriques exonérées fiscalement (art. 91, 91 bis dans leurs plafonds, part des gratifications sous le cumul annuel de 4 000 000, etc.).
5. `BASE_TCS` = `BRUT_IMPOSABLE` − `CNSS_SAL` − `CNAMGS_SAL` ; `TCS` = 5 % × max(0, `BASE_TCS` − 150 000).
6. `BASE_IRPP_M` = `BASE_TCS` − `TCS` ; `BASE_A` = `BASE_IRPP_M` × 12.
7. `ABATT` = min(20 % × `BASE_A`, 10 000 000) ; `RNI` = `BASE_A` − `ABATT`.
8. `Q` = `RNI` / `PARTS` ; `K` = impôt pour 1 part selon le barème ; `IRPP_M` = `K` × `PARTS` / 12, arrondi au franc.
9. Charges patronales : `CNSS_PAT` = 18 % × min(`ASSIETTE_SOC`, 1 500 000) (dont AT 2 %) ; `CNAMGS_PAT` = 4,1 % × min(`ASSIETTE_SOC`, 2 500 000) ; `FNH` = 3 % × min(`ASSIETTE_SOC`, 1 500 000) ; `CFP` = 0,5 % × min(`BRUT` avant déductions, 1 500 000).
10. `NET` = `GAINS` − `CNSS_SAL` − `CNAMGS_SAL` − `TCS` − `IRPP_M` − autres retenues (avances, prêts, cessions, saisies) ; `COÛT EMPLOYEUR` = `GAINS` + charges patronales.

Méthode : c'est la méthode d'annualisation du mois (chaque mois est traité comme 1/12 de l'année). Pour les mois incomplets, les primes irrégulières et le départ en cours d'année, l'addon doit proposer une **régularisation annuelle** (recalcul sur le cumul réel de l'année, écart restitué ou retenu ; ligne « Régularisation IRPP »). 🟡 La DGI accepte la méthode mensuelle ; la régularisation relève de la bonne pratique et de la DAS.

## 8. Exemples de contrôle (calculés par `calcul_paie_gabon_reference.py`)

| | Ex. 1 | Ex. 2 | Ex. 3 | Ex. 4 |
|---|---|---|---|---|
| Situation | Célibataire, 0 enfant | Marié, 2 enfants | Célibataire, 1 enfant | Marié, 3 enfants |
| Gains du mois | 545 000 (dont transport 30 000 exonéré) | 850 000 | 2 000 000 | 5 000 000 |
| Assiette sociale | 515 000 | 850 000 | 2 000 000 | 5 000 000 |
| CNSS salarié 5 % | 25 750 | 42 500 | 75 000 (plafond) | 75 000 |
| CNAMGS salarié 2 % | 10 300 | 17 000 | 40 000 | 50 000 (plafond) |
| Base TCS | 478 950 | 790 500 | 1 885 000 | 4 875 000 |
| TCS | 16 448 | 32 025 | 86 750 | 236 250 |
| Parts | 1 | 3 | 2 | 3,5 |
| RNI annuel | 4 440 019 | 7 281 360 | 17 263 200 | 45 665 000 (abattement plafonné) |
| Quotient Q | 4 440 019 | 2 427 120 | 8 631 600 | 13 047 143 |
| IRPP mensuel | 33 500 | 17 928 | 245 080 | 845 104 |
| **Net à payer** | **459 002** | **740 547** | **1 553 170** | **3 793 646** |
| CNSS employeur 18 % | 92 700 | 153 000 | 270 000 | 270 000 |
| CNAMGS employeur 4,1 % | 21 115 | 34 850 | 82 000 | 102 500 |
| FNH 3 % | 15 450 | 25 500 | 45 000 | 45 000 |
| CFP 0,5 % | 2 575 | 4 250 | 7 500 | 7 500 |
| **Coût employeur** | **676 840** | **1 067 600** | **2 404 500** | **5 425 000** |

Vérification manuelle de l'exemple 2 : TCS = (790 500 − 150 000) × 5 % = 32 025 ; base IRPP annuelle = (790 500 − 32 025) × 12 = 9 101 700 ; RNI = 9 101 700 × 80 % = 7 281 360 ; Q = 7 281 360 / 3 = 2 427 120 → tranche 10 % : 242 712 − 171 000 = 71 712 ; × 3 parts = 215 136 par an, soit 17 928 par mois.
L'exemple 1 reprend les données du support « Architecture de la paie 2026 », qui annonçait un net de 481 507 avec une TCS de 25 343 et un IRPP nul : ces deux montants sont faux (seuil TCS ignoré, quotient non annualisé).
