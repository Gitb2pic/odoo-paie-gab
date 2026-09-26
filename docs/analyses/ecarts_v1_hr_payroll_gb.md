# Écarts de calcul : V1 (`hr_payroll_gb` + `l10n_ga_dgi_edi` V1) ↔ V2 (`l10n_ga_hr_payroll`)

26/09/2026. Source V1 lue : `~/supergel-compta` (commit `222c6f6`), `hr_payroll_gb/data/hr_payroll_data.xml`
(règles salariales), `models/hr_company.py` (taux par défaut), `models/hr_employee.py` (parts).
Aucun code V1 n'est repris (CLAUDE.md §1) ; lecture seule, pour comparaison.
Simulation reproductible : `python3 docs/analyses/comparaison_v1_v2.py` (V1 réécrit en 30 lignes
avec les taux par défaut de `res.company` V1, V2 = noyau `ga_fiscal_core` + YAML).

## 1. Résultat chiffré (paramètres au 30/09/2026, salarié mensuel, sans absence)

| Cas | Net V1 | Net V2 | Écart | Cause principale |
|---|---:|---:|---:|---|
| 150 000, célibataire | 143 250 | 139 500 | −3 750 | CNSS salarié 2,5 % → 5 % |
| 300 000 + 50 000 prime + 20 000 ind. + 10 000 non soumis | 340 781 | 333 048 | −7 733 | idem |
| 590 000, marié 2 enfants | 539 816 | 526 364 | −13 452 | idem |
| 800 000 + 100 000 + 50 000, marié 1 enfant | 837 011 | 817 156 | −19 855 | idem |
| 2 300 000, célibataire | 1 660 569 | 1 634 919 | −25 650 | idem (plafond 1 500 000) |

TCS et IRPP V2 sont **plus faibles** que V1 : conséquence mécanique de la CNSS salariale plus forte
(déduite des deux bases). Hors CNSS, les deux moteurs donnent la même TCS et le même IRPP au franc près
(barème, abattement 20 % plafonné à 10 M/an, parts : identiques).

## 2. Écarts, un par un

| # | Sujet | V1 `hr_payroll_gb` | V2 | Qui a raison (base de connaissance) | Gravité |
|---|---|---|---|---|---|
| E1 | CNSS 2026 | salarié 2,5 %, patronal 16 % (défauts `res.company`, `hr_company.py:21-22`) | salarié 5 %, patronal 5 + 2 + 11 = 18 % dès 01/2026 | V2 (décret 0487/PR/MASI du 18/12/2025, fichier 03 ; fiabilité **probable**) | **forte** : −2,5 % du net |
| E2 | FNH | 2 % (`t_alloc`) | 2 %, puis 3 % dès le 17/07/2026 | V2 si la LFR 2026 art. 403 s'applique (fiabilité **à vérifier**, date de 1re paie à confirmer) | moyenne (charge patronale) |
| E3 | CFP | 0,5 % × (brut + AN − cotisations salariales), **sans plafond** | 0,5 % × min(assiette, 1 500 000) | V2 (YAML : brut avant cotisations, plafond 1,5 M/salarié) | faible |
| E4 | **Prime d'ancienneté** | automatique pour tous dès 24 mois : base × années (fractionnaires) % | uniquement si le salarié a une **convention collective** ; sinon **aucune prime, sans alerte** | V1 sur le résultat ; V2 sur le principe (D-25, point 09-11) | **forte** en démo : 86 salariés sur 106 ont ≥ 2 ans, 1 seul a une convention → 1 seule ligne `GA_ANC` sur 269 bulletins |
| E5 | Heures supplémentaires | majorations fixes +10 % à +100 % | table de la convention, **aucun défaut** ; erreur si heures sans taux | V2 (point 09-11) — mais aucune table n'est saisie en démo (`l10n_ga_overtime_rate` vide) | moyenne |
| E6 | Retenue IRPP minimale | IRPP ≤ 1 000 non retenu | tout est retenu (seuil F14 = 0, D-12) | à trancher (pratique V1 non sourcée) | faible |
| E7 | Indemnités « exonérées » (`INDCNSS` : 13e mois, gratification, prime de bilan, licenciement, transport, représentation…) | **100 % hors TCS/IRPP**, soumises CNSS | exonération plafonnée par groupe (gratifications 4 M/an, transport forfait/jour, véhicule 100 000…) ; 13e mois imposable | V2 (CGI art. 91, instruction 144/2004 ; ADR-17). V1 sous-retient l'impôt | forte chez un client qui verse ces primes |
| E8 | Plancher d'assiette sociale | aucun | SMIG proratisé (décret 599 art. 34) | V2 | faible |
| E9 | Avantages en nature | min(valeur saisie, brut) × taux saisi ; **hors** assiette CNSS | forfait art. 93 sur (brut − cotisations) ; dans l'assiette CNSS | V2 pour le fiscal ; assiette CNSS à confirmer | moyenne |
| E10 | Jours de référence | 21 (`res.company.days`) | 20 (YAML) — base mensuelle 173,33 h dans les deux | à confirmer | faible (absences en jours) |
| E11 | Parts fiscales | table en dur | noyau paramétré | identiques sur tous les cas testés | — |

## 3. Côté DGI

- Le dépôt `supergel-compta` contient la **V1 de `l10n_ga_dgi_edi`** (19.0.4.0.0) : les 4 classeurs
  `static/templates/edi-annexe-ID19/21/23/26.xlsm`, 11 fichiers de tests et les scripts
  `migrations/19.0.3.0.0` et `19.0.4.0.0`. C'est exactement ce qu'attendaient **D-07** (étape 4.5),
  **D-87** (`.xlsm` de la DAS) et l'étape 5 (`.xlsm` des annexes ID23 / ID26).
- Le code de `hr_payroll_gb` donne les modèles et les codes de règles V1 (`BRUT`, `CIMP`, `TCS`,
  `IRPP`, `CNSS`, `FNH`, `CFP`, `WDAYS`…) : base suffisante pour écrire la reprise (étape 6) ;
  D-05 demandait en plus le schéma SQL réel (`pg_dump --schema-only`), à fournir si les tables du
  client divergent du code.
- Les montants déclarés par la V2 (ID10, DTS, DAS) sont la somme des bulletins (écart 0, C-3) :
  ils héritent donc des écarts E1 à E7 ; aucun écart propre aux déclarations n'a été trouvé.

## 4. Ce qui est réellement « faux » dans la V2

1. **E4 — ancienneté silencieuse** : un salarié sans convention n'a pas de prime et aucun contrôle
   avant paie (F8) ne le signale. Contraire à la règle d'or 13 (« jamais un choix silencieux »).
2. **E5 — heures sup. sans table** : même défaut de configuration, mais celui-ci bloque (erreur) au
   lieu de passer sous silence : acceptable, à signaler en contrôle avant paie.
3. E1, E2 et E7 : la V2 applique les textes 2026 ; la V1 est en retard. Ce n'est un défaut V2 que si
   la réforme CNSS ou la LFR 2026 ne s'appliquent pas encore chez le client.

Décisions à prendre : D-105 à D-110 (`docs/decisions/ouvertes.md`).
