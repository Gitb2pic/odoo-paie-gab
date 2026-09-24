# 06 — Déclarations sur salaires : ID10, ID28 et DAS (ID19 à ID26)

Toutes les références de cellules renvoient aux modèles Excel du dossier source. La colonne « Source Odoo » indique d'où l'addon doit tirer la donnée (voir aussi fichier 08).

## 1. ID10 — Retenue à la source sur salaires et contribution à la formation professionnelle

Périodicité : mensuelle. Échéance : **le 15 du mois suivant le paiement des salaires** (art. 95, 96 et 206 du CGI ; art. 10 LFR 2017). Deux exemplaires. Le dépôt doit s'accompagner du paiement.

### En-tête

| Cellule | Donnée | Source Odoo |
|---|---|---|
| H15 / P15 | Exercice / mois | période de la déclaration |
| A17 | NIF (numéro d'identification fiscale) | `res.company` champ NIF |
| A23, B25 | Raison sociale, sigle | `res.company` |
| A27 → A31 | BP, ville, téléphone, télécopie, e-mail, site | `res.company` / `res.partner` |
| K33 | Code résidence (centre des impôts d'affectation) | paramètre société |

### Cadre 2 — Retenues sur salaires à payer

| Ligne | Désignation | Calcul | Source Odoo |
|---|---|---|---|
| B40 / P40 | Impôt sur le revenu des personnes physiques | Σ IRPP retenu sur les bulletins payés dans le mois | règle `IRPP` |
| B41 / P41 | Taxe complémentaire sur les traitements et salaires | Σ TCS | règle `TCS` |
| B42 / P42 | Prélèvement pour le Fonds national de l'habitat | Σ FNH (3 % depuis LFR 2026) | règle `FNH_PAT` (+ `FNH_SAL` si répartition) |
| P43 | Montant global dû | = P40 + P41 + P42 | calcul |
| V39 | Code rubrique | codes recette DGI | 🔴 table des codes à obtenir |

### Cadre 3 — Contribution à la formation professionnelle

| Ligne | Désignation | Formule du modèle | Formule correcte à coder |
|---|---|---|---|
| L1 (R49) | Salaire de base | saisie | Σ salaires de base (plafonnés par salarié à 1,5 M avec L2) |
| L2 (R50) | Avantages en numéraire | saisie | Σ primes et indemnités en espèces soumises |
| L3 (R51) | Montant des cotisations CNSS | saisie | Σ CNSS salariales |
| L4 (R52) | Montant des cotisations CNAMGS | saisie | Σ CNAMGS salariales |
| L5 (R53) | Avantages en nature = (L1 + L2 − L3 − L4) × taux art. 93 | `=R49+R50-R51-R52` ❌ n'applique aucun taux | Σ des avantages en nature réellement valorisés (logement 6 %, domesticité 5 %, eau/électricité 5 %, nourriture 25 % ≤ 120 000) |
| L6 (R54) | Base CFP = L1 + L2 + L5 | `=R49+R50+R53` | idem, en plafonnant chaque salarié à 1 500 000 |
| L7 (R55) | Taux | 0,005 | paramètre `cfp_taux` |
| R56 | Montant global dû = L6 × L7 | `=R54*R55` | idem |

### Cadre 4 — Règlement

Mode : espèces (< 500 000), chèque (< 100 000 000), virement (≥ 100 000 000 ; obligatoire pour DGE/CIME et au-delà de 500 000 selon la LF 2026), IBAN/BIC, n° de quittance, date. Remplissage manuel ou depuis le paiement comptable.

## 2. ID28 — Contribution à la formation professionnelle (déclaration séparée)

Même échéance (le 15). Lignes : L1 salaires de base, L2 avantages en numéraire, L3 cotisations CNSS, **L4 avantages en nature = (L1 + L2 − L3) × taux art. 93** (la CNAMGS n'est pas déduite, contrairement à l'ID10), L5 base = L1 + L2 + L4, L6 taux 0,5 %, montant = L5 × L6.
Pour l'addon : produire le cadre CFP soit dans l'ID10, soit sur l'ID28, selon le choix de la société (paramètre) ; ne jamais déclarer la CFP deux fois. 🔴 L'usage actuel du centre des impôts (ID10 seul ou ID10 + ID28) est à confirmer.

## 3. DAS — Déclaration annuelle des salaires

Base légale : art. 167 ter CGI (LF 2017) : état nominatif de tous les salariés de l'année précédente à déposer **au plus tard le 30 avril**. Art. 90 (ID21/ID22) et art. 189 (ID23/ID24), art. 182 et 189 (ID26). Les anciennes mentions « avant le 31 janvier » / « avant le 28 février » des modèles 2019 sont caduques.
Le fichier `Fichier_DAS - v3.xlsx` (impots-et-taxes.com) alimente tous les imprimés à partir de deux onglets source ; l'addon doit reproduire cette logique en lisant directement les bulletins validés de l'année.

### 3.1 Données source par salarié (onglet `source_salaires`)

| N° col. | Champ | Source Odoo |
|---|---|---|
| 1-2 | N° matricule, N° CNSS | `hr.employee` (matricule, n° CNSS) |
| 3-5 | Nom, prénom, profession | `hr.employee`, `hr.job` |
| 6-7 | Code emploi, code niveau | 🔴 nomenclature DGI à obtenir ; champs à créer |
| 8 | Nationalité : 1 Gabonais, 2 CEMAC, 3 autres africains, 4 non africains | calcul depuis `country_id` |
| 9 | Âge (au 01/01) | `birthday` |
| 10 | Sexe : 1 masculin, 2 féminin | `gender` |
| 11 | Situation familiale : 1 marié, 2 célibataire, 3 veuf, 4 divorcé | `marital` |
| 13 | Nombre d'enfants | `children` |
| 14-17 | Période : jour/mois de début, jour/mois de fin | contrat / dates de paie de l'année |
| (1) | Salaire brut de présence | Σ gains imposables hors congés, hors AN, hors indemnités imposables |
| (2) | Avantages en nature : logement, eau & électricité, domesticité | Σ rubriques AN_* |
| (3) | Nourriture | Σ AN_NOUR |
| (4) | Indemnités imposables (partie 657) | Σ indemnités imposables |
| (5) | Salaire brut de congé | Σ allocations de congé |
| (6) | Total (1 à 5) | somme |
| (7) | TCTS retenue | Σ TCS |
| (8) | IRPP retenu | Σ IRPP (après régularisations) |
| (9) | CFP | Σ CFP |
| (10) | FNH | Σ FNH |
| (11) | Total (7 + 8 + 9 + 10) | somme |
| — | Indemnités non imposables : logement, transport, domesticité/gaz, autres, total | Σ rubriques exonérées par nature |
| calcul | Moyenne mensuelle = (indemnités non imposables + congé + indemnités imposables + brut de présence) / 12 | classe « A » si ≥ 1 000 000, sinon « B » (ID20) |

Remarque DGI (ID19) : les montants sont pris **après déduction des retenues pour retraite et sécurité sociale** (CNSS/CNAMGS salariales) et avant déduction des retenues pour logement, nourriture, etc. 🟡 La colonne (1) de l'ID21 doit donc être nette des cotisations salariales pour être cohérente avec l'ID19 et l'ID20 (« prendre les salaires bruts versés après déduction des retenues pour retraite et sécurité sociale »).

### 3.2 Imprimés produits

| Imprimé | Contenu | Règles de génération |
|---|---|---|
| **ID19** Bulletin individuel de justification | Par salarié percevant plus de 80 000 FCFA/mois (et par bénéficiaire d'honoraires) : identité, NIF, situation, enfants, période ; montant versé (présence, congés, rappels des années antérieures) ; avantages en nature (6 %, 5 %, 5 %, 25 % plafonné) ; allocations pour frais non déductibles (art. 91 bis) ; total brut ; à déduire TCS de l'année ; rémunération brute imposable ; IRPP retenu ; indemnités non imposables (logement, transport, gaz, autres) ; cadre 3 pour les non-salariés (administrateurs, courtiers, honoraires) | 1 PDF par salarié éligible |
| **ID20** État de la masse salariale | Nombre de salariés et total des rémunérations pour 2 tranches : < 1 000 000 et ≥ 1 000 000 FCFA/mois | agrégat |
| **ID21** Bordereau détaillé | 1 ligne par salarié (39 lignes par feuille dans le modèle) : colonnes 1 à 11 de la section 3.1 + indemnités non imposables | pagination automatique |
| **ID22** Bordereau récapitulatif | Totaux par feuille d'ID21 ; tableau des versements mensuels (12 mois × lignes RS et FNH, montant, date et n° de quittance) ; contrôle « total versé (col. 12) = total des retenues (col. 10) », sinon note explicative | les versements viennent des paiements ID10 comptabilisés |
| **ID23** Commissions, honoraires versés au Gabon (art. 189) | Bénéficiaires salariés (A) et non-salariés (B) : nom, NIF, profession, sommes versées. L'admission en charges est subordonnée à la production d'un ID19 | depuis les factures fournisseurs marquées « honoraires/commissions » |
| **ID24** Commissions, honoraires versés hors du Gabon (art. 189) | CEMAC / hors CEMAC : nom, adresse, montant versé, retenue à la source effectuée | depuis les factures fournisseurs non résidents + RAS (ID27) |
| **ID26** Prestataires non assujettis à la TVA (art. 182 et 189) | Nom, NIF, montant versé, retenue 9,5 % | depuis les factures + précomptes ID18 |

### 3.3 Anomalies relevées dans `Fichier_DAS - v3.xlsx` (à ne pas reproduire)

1. **ID22** : le total des retenues `X16 = Q16 + U16 + W16` exclut la CFP (colonne V) et la colonne V n'est pas totalisée en ligne 46 ; le total doit être TCTS + IRPP + CFP + FNH.
2. **ID22** : le nombre de salariés par feuille (colonne B) n'est pas calculé.
3. **ID23** : la colonne NIF des bénéficiaires non salariés (`X17`) cherche la clé en `O17` (montant) au lieu de `T17`.
4. **ID23** lignes 78 et suivantes : la colonne « sommes versées » lit le type de prestation (colonne I) au lieu du montant (colonne X).
5. **ID19-salarié** : téléphone, BP et ville (`D16`, `I16`, `N16`) sont lus dans l'onglet des honoraires et testés sur de mauvaises cellules de verrouillage (`BJ3/BJ4`).
6. **source_honoraires** : la retenue 9,5 % (colonne V, si non assujetti TVA) et la retenue 20 % (colonne W, si pays ≠ Gabon) peuvent se cumuler pour un prestataire étranger non assujetti ; un non-résident ne doit subir que la RAS non-résidents.
7. **ID19-P** (honoraires, ligne c) : cherche le montant par NIF dans la colonne X (TTC) au lieu du montant HT par type C.
8. **ID20** : le classement < 1 M / ≥ 1 M inclut les indemnités non imposables dans la moyenne mensuelle, alors que l'imprimé parle de « salaire brut » : 🔴 à confirmer.
9. Dates de dépôt figées (« 30/04/2017 ») et verrouillage du fichier par concaténation raison sociale + exercice : à remplacer par la date légale calculée.

## 4. Contrôles de cohérence à implémenter

- Σ IRPP + TCS + FNH des 12 ID10 de l'année = totaux ID21 colonnes (7), (8), (10) = grille des versements ID22.
- Σ CFP des 12 déclarations mensuelles = total colonne (9).
- Chaque salarié payé dans l'année figure dans l'ID21 ; chaque salarié dont la moyenne mensuelle dépasse 80 000 a un ID19.
- Total ID20 = total colonne (6) de l'ID21 (même définition de la base).
- Écart entre le cumul IRPP retenu et l'IRPP recalculé sur l'année (régularisation) signalé avant la clôture.
- Masse salariale DAS rapprochée des comptes 661-663 et des DTS CNSS/CNAMGS (écarts expliqués par les éléments non soumis).
