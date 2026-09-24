# 03 — Cotisations sociales : CNSS et CNAMGS

## 1. Taux et plafonds applicables en 2026 ✅

Source : décret n°0487/PR/MASI du 18/12/2025 (réforme CNSS), fiche CLEISS « Les cotisations au Gabon » mise à jour au 01/01/2026, presse (Gabonreview, L'Union, Gabonmediatime, janvier 2026), guide CC&F 2026.

| Organisme | Branche | Salarié | Employeur | Plafond mensuel |
|---|---|---|---|---|
| CNSS | Prestations familiales et maternité | — | 5 % | 1 500 000 |
| CNSS | Accidents du travail et maladies professionnelles | — | 2 % | 1 500 000 |
| CNSS | Vieillesse, invalidité, décès (AVID / pensions) | 5 % | 11 % | 1 500 000 |
| **CNSS total** | | **5 %** | **18 %** | 1 500 000 |
| CNAMGS | Assurance maladie (régime général) | 2 % | 4,1 % | 2 500 000 |
| **Total social** | | **7 %** | **22,1 %** | |

Historique (avant la réforme, jusqu'à la paie de décembre 2025) : CNSS salarié 2,5 %, employeur 16 % (PF 8 + AT 3 + pensions 5), plafond 1 500 000 ; CNAMGS inchangée (4,1 % = anciens 0,6 % évacuations sanitaires + 2 % médicaments + 1,5 % hospitalisation).

Date d'effet : la presse indique une application au 1er janvier 2026, avec des arrêtés d'application et un délai d'adaptation des logiciels. 🟡 L'addon doit gérer les taux par date d'effet (voir fichier 08) afin de pouvoir recalculer rétroactivement si la date d'application effective diffère.

Plafonds : ils s'apprécient par mois, mais la régularisation annuelle se fait sur le plafond annuel (18 000 000 pour la CNSS) en faisant masse des rémunérations de l'année (décret 599, art. 39). Un salarié qui dépasse le plafond certains mois et pas d'autres peut donc générer une régularisation en fin d'année. 🟡 La pratique courante applique le plafond mensuellement ; l'addon doit proposer la régularisation annuelle en option.

Autres règles d'assiette :

- Assiette minimale = SMIG (80 000 FCFA), même si le salaire est inférieur (décret 599, art. 34) ; apprentis et stagiaires cotisent sur le SMIG pour la branche risques professionnels (art. 11).
- Primes et éléments irréguliers : ajoutés à la paie du mois où ils sont versés (art. 36) ; le plafond du mois s'applique alors au total.
- Salarié à employeurs multiples : chaque employeur cotise sur la part de plafond proportionnelle à ce qu'il paie (art. 37).
- Gens de maison : cotisation forfaitaire trimestrielle fixée par décret (art. 35).

## 2. Assiette des cotisations : quelles rubriques sont soumises ? ✅

Texte : arrêté n°016/MTEPS d'avril 2010 (fichier 01, A3) combiné à l'arrêté n°037/MTEPS du 22/07/2010.

**Soumis** (liste non limitative, art. 2) : salaire de base, heures supplémentaires, sursalaire, prime d'ancienneté, différentiel, allocation de congés, toutes gratifications (13e, 14e mois, fin d'année, rendement, performance, bonus, bilan, résultat, exceptionnelle, intéressement), primes de responsabilité, professionnelle, d'équipe, d'assiduité, de bâche, de représentation, de nuit, de pénibilité, de vacances, de vie chère, de diplôme, de sujétion, de confort, de risque, de technicité, indemnité de préavis, **indemnité de licenciement**, ISR (50 % en cas de retraite, 100 % en cas de démission), indemnité de logement, d'éloignement/brousse/expatriation, de fonction, commissions, pourboires, complément employeur aux indemnités journalières, avantages en nature (évalués selon le CGI).

**Exclus** (art. 3) : indemnités de déplacement, de mission, de voyage, de caisse, de blanchissage, de repas, de panier, de froid, de chaleur, de frais de scolarité, kilométrique ; primes de salissure, vestimentaire, de beauté, de coiffure ; frais de formation, d'insalubrité ; jetons de présence ; indemnité de comité d'entreprise ; ISR versée en cas de départ volontaire dans un plan social ; prime de solidarité ; prestations sociales autorisées par la CNSS et prestations du Code de sécurité sociale.

**Cas particulier des frais de déplacement domicile-travail** : l'arrêté 016 met l'indemnité de transport et de véhicule dans l'assiette, mais l'arrêté 037/MTEPS exonère **transport + véhicule + kilométrique + carburant dans la limite cumulée de 35 000 FCFA par mois et par salarié** ; l'excédent est cotisable. 🟡
Condition générale : un forfait n'est exclu que si l'employeur peut prouver qu'il a été utilisé conformément à son objet (art. 4).

## 3. Déclaration et paiement

| Organisme | Déclaration | Périodicité | Délai | Mode |
|---|---|---|---|---|
| CNSS | Déclaration trimestrielle des salaires (DTS) : nominative, par salarié, avec salaires du trimestre | Trimestrielle | dans les 30 jours suivant le trimestre (30/01, 30/04, 30/07, 30/10) | Portail CNSS / imprimé |
| CNAMGS | DTS CNAMGS | Trimestrielle | paiement du 1er au 30 du mois suivant le trimestre | e-déclaration (edeclaration.cnamgs.ga) |

Mouvements de personnel : feuille d'immatriculation (première embauche), certificat d'embauchage (salarié déjà immatriculé) et certificat de cessation de travail, dans les **8 jours** (décret 599, art. 1 à 3). Le bulletin doit porter le numéro d'affiliation de l'employeur et le numéro d'immatriculation du salarié (art. 6).

## 4. Prestations gérées en paie

- **Maternité** : 14 semaines ; indemnité journalière CNSS = rémunération du mois précédant la suspension / 30 (décret 599, art. 69) ; si l'employeur maintient le salaire, il est subrogé dans les droits de la salariée à hauteur du salaire versé (art. 72) → l'addon doit pouvoir enregistrer une créance CNSS et la solder à réception.
- **Accident du travail** : l'indemnité journalière avancée par l'employeur est remboursée par la Caisse (art. 94).
- **Prestations familiales** : versées par la CNSS ; un employeur d'au moins 10 salariés peut être autorisé à les payer lui-même et à les compenser avec ses cotisations, avec une ristourne de 2 % (art. 77-79).
- **Allocation de rentrée scolaire** : 10 000 FCFA par enfant, payée par l'employeur au 1er septembre sur bordereau CNSS, avec remboursement par la CNSS (arrêté 4/MSSBE-DGSS de 1982). 🟡 montant historique à confirmer.
- **Retraite (information)** : pension de 40 % du salaire moyen (meilleure moyenne des 3 ou 5 dernières années) + 1 % par année au-delà de 240 mois (décret 599 art. 8, exemple ULYSS). La réforme 2025 modifie les conditions (âge légal auparavant 55 ans) : 🔴 hors périmètre paie.

## 5. Pour l'addon

- Paramètres datés : `cnss_taux_salarial`, `cnss_taux_pf`, `cnss_taux_at`, `cnss_taux_avid_pat`, `cnss_plafond`, `cnamgs_taux_salarial`, `cnamgs_taux_patronal`, `cnamgs_plafond`, `smig`, `plafond_exo_transport_social` (35 000).
- Chaque rubrique de gain porte un indicateur « soumis CNSS/CNAMGS » (oui / non / plafonné) conforme à la section 2.
- Règles : `ASSIETTE_SOC = max(SMIG × taux_présence, somme des gains soumis + excédent transport au-delà de 35 000)` ; `CNSS_SAL = min(ASSIETTE_SOC, 1 500 000) × 5 %` ; `CNAMGS_SAL = min(ASSIETTE_SOC, 2 500 000) × 2 %` ; idem pour les parts patronales, la part AT étant isolée pour permettre un taux AT spécifique si la CNSS le fixe par entreprise.
- Sorties : état DTS CNSS et DTS CNAMGS trimestriels par salarié (matricule CNSS, nom, salaires des 3 mois, cotisations), rapprochement avec les comptes 431/432.
- Comptabilité (SYSCOHADA) : cotisations patronales au débit du 664, parts salariales et patronales au crédit du 431 (CNSS) et d'un sous-compte 431x (CNAMGS).
