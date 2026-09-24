# 07 — Autres impôts de l'entreprise (hors paie)

Ce fichier couvre les imprimés du dossier qui ne relèvent pas de la paie, pour préparer la V2 (ID01 était reporté en V2) et les modules comptables associés.

## 1. Impôt sur les sociétés (ID01, ID02, ID03)

| Élément | Règle | Fiabilité |
|---|---|---|
| Taux normal | 30 % du bénéfice imposable | ✅ (modèle ID01, PwC 2026) |
| Pétrole et mines | 35 % | ✅ PwC |
| Autres taux | Le PDF ID01 renvoie à « 18 %, 20 % ou 35 % (art. 16) » ; impots-et-taxes cite un taux réduit de 25 % | 🔴 à vérifier (régimes particuliers) |
| Minimum de perception / IMF (art. 24 ; art. 62) | 1 % du chiffre d'affaires global de l'exercice, avec un minimum | ✅ taux / 🔴 minimum : 1 000 000 (modèle ID01, impots-et-taxes) ou 500 000 (PwC 2026) |
| Impôt dû | max(IS brut, minimum de perception) | ✅ |
| Imputations | 1er et 2e acomptes, précompte sur achats de grumes (art. 22), précompte sur prestations de service (art. 23) | ✅ |
| Crédits d'impôt | nouvelles embauches (art. 16 a), tourisme (art. 16 b), crédits antérieurs N-3 à N-1 ; LFR 2026 : crédit pour dispositifs de facturation électronique (25 % / 25 % / 50 % sur 3 ans) | ✅ |
| 1er acompte (ID02) | 25 % de l'IS de l'exercice précédent, au plus tard le 30 novembre N | ✅ |
| 2e acompte (ID03) | 33,33 % de l'IS de l'exercice précédent, au plus tard le 30 janvier N+1 | ✅ |
| Solde (ID01) | au plus tard le 30 avril N+1, avec la DSF (tableaux 1 à 34, annexes 1 et 2), relevé des rémunérations des associés, déclarations ID20 à ID27 | ✅ |
| Codes rubrique acomptes | 10 hors mines/pétrole, 18 mines, 25 pétrole | ✅ |
| Charges déductibles | uniquement si appuyées de factures électroniques normalisées (art. 11, LF et LFR 2026) | ✅ |
| Plus-values de cession de droits sociaux | prélèvement libératoire 25 % reversé sous 1 mois par la société dont les titres sont cédés (art. 23 al. 6) | ✅ |

Structure ID01 : page 1 identification (NIF, comptable salarié ou cabinet, activité), page 2 détermination (lignes 0 à 17), page 3 solde à payer (18), reports (19), règlement, page 4 renseignements juridiques et capital social.
Anomalie du modèle : la cellule T2 de la page 3 additionne des plages (`'Page 2'!T33:W33`) au lieu de cellules ; la ligne 14 (crédit) n'est pas calculée.

## 2. TVA et contribution spéciale de solidarité (CA01, CA02, ID30)

| Élément | Règle | Fiabilité |
|---|---|---|
| Taux TVA | 18 % normal ; 10 % et 5 % réduits (listes de produits art. 221) ; 3 % fer à béton fabriqué au Gabon (LFR 2026) ; 0 % exportations et transport international | ✅ (listes modifiées deux fois en 2026) |
| Déduction | uniquement sur factures électroniques normalisées (art. 223) ; droit à déduction à l'exigibilité chez le fournisseur ; omissions réparables jusqu'au 12e mois (art. 222, LFR 2026) | ✅ |
| Prorata (art. 227, LFR 2026) | ≤ 10 % : aucune déduction ; > 90 % : déduction totale ; entre les deux : pourcentage réel | ✅ |
| Précompte TVA sur marchés publics | 40 % de la TVA due retenue par le Trésor (art. 239, LF 2017) | 🟡 |
| CSS | 1 % du chiffre d'affaires HT (base déterminée comme la TVA, hors services liés aux activités minières et pétrolières), redevables dont le CA HT annuel ≥ 30 000 000 FCFA | ✅ LF 2017 |
| Échéance | le 20 de chaque mois, CSS payée avec la déclaration de TVA (CA01) ou sur ID30 | ✅ |
| Non-résidents numériques | immatriculation simplifiée, déclaration trimestrielle (20 jours), TVA + CSS (art. 248 septies à nonies, LFR 2026) | ✅ |

CA01 — lignes : 1 opérations non imposables, 2 exportations, 3 opérations imposables HT (par taux), 4a/4b opérations avec l'État et autres (LASM), 5 base TVA, 6 total, 7a/7b déductions biens et services (import / intérieur), 8a/8b immobilisations, 9a à 9d régularisations (précompte État, dispense, compte de tiers, complément), 10a/10b remboursement demandé / reversement, 11 report de crédit, 12 TVA import à paiement différé, 13 total déductible (avec pourcentage de déduction), 14 TVA brute par taux, 15 total TVA brute, 16 TVA déductible, 17 TVA nette à payer, 18 crédit à reporter, 19 crédit import ; cadre II CSS (lignes 1 à 5) ; annexe « compte de tiers » (TVA art. 240, CSS art. 29 LFR 2017).
CA02 — demande de remboursement de crédit : crédit (ligne 18 CA01), plafond exportateurs (ventes × taux), montant = min(crédit, plafond) pour les exportateurs. Anomalie : les formules de la CA02 pointent vers des cellules de la CA01 qui ne correspondent pas aux libellés.
Pour l'addon : ne pas coder les listes de produits ; s'appuyer sur les taxes Odoo (`account.tax`) avec des tags de grille de rapport pour alimenter chaque ligne de la CA01.

## 3. Retenues et précomptes à la source

| Imprimé | Objet | Taux | Échéance | Source | Fiabilité |
|---|---|---|---|---|---|
| ID18 | Précompte sur prestations de services des prestataires relevant de l'IRPP (BIC/BNC) non assujettis à la TVA | 9,5 % | le 15 du mois suivant | art. 182 | ✅ |
| ID26 (annuel, DAS) | Récapitulatif des sommes versées aux prestataires non assujettis et des retenues de 9,5 % | — | 30 avril | art. 182 et 189 | ✅ |
| ID27 | Retenue à la source sur rémunérations versées à des non-résidents sans établissement stable (services, droits, intérêts…) | 20 % du montant brut HT (modèle, impots-et-taxes) — PwC 2026 indique 25 % | le 15 du mois suivant | art. 206 | 🔴 |
| ID24 (annuel, DAS) | Récapitulatif des sommes versées hors du Gabon (CEMAC / hors CEMAC) et des retenues | — | 30 avril | art. 189 | ✅ |
| ID09 | Taxe spéciale immobilière sur les loyers (TSIL) retenue par le locataire personne morale | 15 % des loyers | Excel : le 15 du mois suivant ; PDF 2014 : le 15 du 1er mois du trimestre | art. 388 | 🟡 |
| ID31 | Précompte IRPP sur revenus fonciers (bailleur hors IS) | LF 2017 : 5 % mensuel ; LF 2026 : 10 %, trimestriel ; LFR 2026 : 5 % | 15 premiers jours du trimestre suivant (LF 2026) | art. 178 bis | 🟡 taux 5 % depuis la LFR ; périodicité à confirmer |
| — | IRCM (dividendes) | 20 % | selon distribution | — | ✅ |
| — | Prélèvement plus-values de cession de titres | 25 % | 1 mois | art. 23 al. 6 | ✅ |

Conventions fiscales : la convention OCAM cesse de s'appliquer au Gabon à compter du 01/01/2026 (LFR 2026, art. 7) ; les conventions bilatérales (France, Belgique, Canada, Maroc, Chine, Italie…) restent applicables.

## 4. Impôts professionnels et fonciers

| Impôt | Régime 2026 | Imprimé du dossier | Statut |
|---|---|---|---|
| Patente | 0,1 % du CA HT de l'exercice précédent (base IMF art. 62), minimum 150 000, maximum 10 000 000 FCFA ; déclarée et payée avant le 1er mars ; exonérations art. 254 (1er exercice des entreprises nouvelles, IS libératoire, exploitants miniers…) | CP04 (ancien acompte = patente N-1, avant le 28/02) | 🔴 modèle obsolète |
| Contribution foncière unique (CFU) — personnes morales | Base = valeur locative réelle (ou 10 % de la valeur bilancielle ; valeur réelle si la valeur au bilan est inférieure de plus de 20 %), abattement 5 % (sauf terrains nus), taux 15 %, base arrondie au millier inférieur | TP01 / TP02 (anciennes CFPB/CFPNB : abattement 25 %, 80 % × 10 %, taux 25 %) | 🔴 modèles obsolètes |
| CFU — personnes physiques | Forfait selon zone (1 centre-ville à 4 rural) et tranche de valeur (bâti : de 25 000 à 1 139 177 FCFA en zone 1) ou de superficie (non bâti) ; terrains agricoles : valeur vénale forfaitaire à l'hectare (6 000 café/cacao/palmier/hévéa, 500 autres cultures, 150 autres) | — | ✅ |
| Échéance CFU | déclaration et paiement au plus tard le 30 mars ; l'administration notifie le montant avant le 1er janvier | — | ✅ |
| Taxe forfaitaire d'habitation | 500 à 30 000 (particuliers), 1 000 à 50 000 (entreprises), collectée mensuellement sur la facture d'électricité | — | ✅ |

## 5. Régime simplifié et sociétés civiles

- **ID13** (BIC/BNC/BA au régime simplifié) : bénéfice = CA − abattement forfaitaire (art. 143) de 70 % (achat-revente, production), 50 % (prestations de services), 40 % (professions libérales) ; report en ligne 3C1 de la déclaration IRPP ; dépôt au plus tard le 30 avril N+1 (art. 158). Anomalie du modèle : la formule du bénéfice référence la mauvaise ligne et soustrait les trois abattements au lieu d'un seul.
- **ID15** (sociétés civiles non soumises à l'IS) : revenu foncier = loyers encaissés − abattement forfaitaire 30 % ou frais réels (option irrévocable 3 ans, art. 89) − charges (intérêts d'emprunt, TSIL, contributions foncières — désormais CFU) ; déficit reportable 3 exercices ; état par associé.
- **Régime fiscal simplifié des sous-traitants pétroliers** (art. 47, 148) : IS 5,95 % du CA, impôts sur salaires 2,80 % du CA (impots-et-taxes). 🟡

## 6. Facturation électronique normalisée (FNE) — impact transversal

Obligatoire pour toute opération d'un assujetti à l'IS, à l'IBP, à l'IS libératoire ou à la TVA, via un dispositif homologué par la DGI (P-832 ter) ; mentions obligatoires listées à l'art. P-832 quinquies (NIF fournisseur et client, type de client, code du dispositif, éléments de sécurité, précomptes, impôt retenu à la source…). Conséquences : charge non déductible et TVA non récupérable sans FNE ; amendes P-1005. Les logiciels de facturation d'entreprise (dont Odoo) doivent être homologués, sous peine d'amende de 5 000 000 FCFA (10 000 000 en récidive).
Pour l'addon et le projet : hors périmètre paie, mais à signaler au client ; la comptabilisation des factures fournisseurs devra porter l'identifiant FNE pour sécuriser la déductibilité.
