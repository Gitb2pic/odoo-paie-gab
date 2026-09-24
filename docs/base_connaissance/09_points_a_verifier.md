# 09 — Points à vérifier (contradictions et ambiguïtés)

Chaque point indique l'hypothèse retenue par défaut dans la base et dans le paramétrage proposé. À trancher avec la DGI, la CNSS, la CNAMGS ou un fiscaliste avant la mise en production.

| # | Sujet | Contradiction / ambiguïté | Hypothèse par défaut | Qui peut trancher |
|---|---|---|---|---|
| 1 | Date d'effet des taux CNSS 2026 | Décret du 18/12/2025, presse « au 1er janvier 2026 », mais « conditionné à des arrêtés d'application » avec délai d'adaptation | Paie de janvier 2026 ; paramètre daté modifiable | CNSS (communiqué officiel) |
| 2 | FNH 3 % : répartition et date | Loi 002/2026 : redevable = employeur, mais débat public sur une répercussion au salarié ; date de première application non précisée | 100 % employeur, à partir de la première paie suivant la promulgation (17/07/2026) | DGI / texte d'application |
| 3 | Déduction de la CNAMGS salariale dans la base TCS (et IRPP) | Aucun texte consulté ne la mentionne explicitement ; anciens textes : « brut − CNSS » | Déduite (paramètre `tcs_deduit_cnamgs = vrai`) | DGI |
| 4 | Exonération des gratifications ≤ 4 000 000/an | Issue d'une instruction de 2004 ; non retrouvée dans les sources 2026 | Appliquée via un compteur annuel, désactivable | DGI |
| 5 | Indemnité de logement en espèces | « Fraction qui dépasse 250 000 FCFA ou 40 % du brut » : on ne sait pas s'il faut retenir le plus faible ou le plus élevé des deux seuils, ni comment l'articuler avec le forfait de 6 % (le cas ULYSS impose min(indemnité, 6 % du brut)) | Exonération jusqu'au plus faible des deux seuils ; excédent imposable ; option alternative paramétrable | DGI / fiscaliste |
| 6 | Base de l'ID21 et de l'ID20 | L'ID19/ID20 demandent les salaires « après déduction des retenues pour retraite et sécurité sociale » ; le modèle v3 reprend des bruts et inclut les indemnités non imposables dans le classement ≥ 1 M | Colonne (1) nette des cotisations salariales ; classement ID20 sur la moyenne des rémunérations imposables | DGI (centre des impôts) |
| 7 | RAS non-résidents | 20 % (modèle ID27, impots-et-taxes) contre 25 % (PwC 2026) | 20 %, paramétrable | DGI / texte CGI art. 206 à jour |
| 8 | Minimum de l'IMF | 1 000 000 (modèle ID01, impots-et-taxes) contre 500 000 (PwC 2026) | 1 000 000, paramétrable | CGI art. 62 à jour |
| 9 | Précompte IRPP loyers (ID31) | LF 2017 : 5 % mensuel ; LF 2026 : 10 % trimestriel ; LFR 2026 : 5 % (périodicité non précisée dans le résumé) | 5 %, trimestriel | Texte intégral LFR 2026 |
| 10 | Périodicité de la TSIL (ID09) | Excel : le 15 de chaque mois ; PDF 2014 : le 15 du 1er mois de chaque trimestre | Mensuelle | Centre des impôts |
| 11 | Majorations des heures supplémentaires | Valeurs divergentes selon les sources, décret non cité | Table par convention collective, aucun défaut | Convention du client / inspection du travail |
| 12 | Taux IS particuliers | Note du PDF ID01 « 18 %, 20 % ou 35 % » ; taux réduit 25 % cité ailleurs | 30 % ; 35 % pétrole/mines | CGI art. 16 à jour |
| 13 | Transport : exonération fiscale | Plafond journalier (2 500 / 5 000) de 1987-2010 : toujours applicable ? Et carburant/kilométrique non listés à l'art. 91 bis | Plafond journalier × jours de présence ; carburant imposable | DGI |
| 14 | Régularisation annuelle CNSS sur plafond annuel | Décret 599 art. 39 vs pratique mensuelle | Plafond mensuel, régularisation optionnelle | CNSS |
| 15 | Montant de l'allocation de rentrée scolaire | 10 000 FCFA (arrêté 1982), jamais revalorisé ? | 10 000, paramétrable | CNSS |
| 16 | Code rubrique ID10 et nomenclature « code emploi / code niveau » DAS | Non fournis dans les documents | Champs libres | DGI |
| 17 | Échéance le week-end ou jour férié | Aucun texte trouvé | Pas de report | DGI |
| 18 | Barème du document `BAREME-IRPP.pdf` | Barème 0/8/15/28/40 % sans rapport avec le CGI | Écarté | — |

## Sources consultées sur Internet

- CLEISS, « Les cotisations au Gabon » (mise à jour 01/01/2026) : https://www.cleiss.fr/docs/cotisations/gabon.html
- Gabonmediatime, « Cotisations sociales : ce que le nouveau décret change concrètement » : https://gabonmediatime.com/cotisations-sociales-ce-que-le-nouveau-decret-change-concretement-pour-les-travailleurs/
- L'Union, « Réforme des cotisations sociales : ce que le décret change concrètement » : https://www.union.sonapresse.com/fr/reforme-des-cotisations-sociales-ce-que-le-decret-change-concretement
- Gabonreview, « CNSS : le doublement de la part salariale… » (06/01/2026) : https://www.gabonreview.com/cnss-le-doublement-de-la-part-salariale-garantira-t-elle-la-survie-du-modele-social-au-prix-du-pouvoir-dachat/
- PwC Worldwide Tax Summaries Gabon — Individual, taxes on personal income (revue 06/08/2026) : https://taxsummaries.pwc.com/gabon/individual/taxes-on-personal-income
- PwC — Corporate income, withholding taxes, tax administration : https://taxsummaries.pwc.com/gabon/corporate/taxes-on-corporate-income
- Loi de finances rectificative 2026 (PDF, Direct Infos Gabon) : https://directinfosgabon.com/wp-content/uploads/2026/07/LFR2026.pdf
- Gabonreview, « Logement : 3 % de plus sur la fiche de paie… » (26/07/2026) : https://www.gabonreview.com/logement-3-de-plus-sur-la-fiche-de-paie-un-flou-sur-qui-paiera-vraiment/
- Gabon24, « Fonds national de l'habitat : comprendre la réforme de 3 % » : https://gabon24.tv/economie/fonds-national-de-l-habitat-comprendre-la-reforme-de-3-destinee-a-financer-les-logements-des-gabonai
- Deloitte Avocats, « Gabon : les principales mesures de la loi de finances pour 2026 » : https://blog.avocats.deloitte.fr/gabon-les-principales-mesures-de-la-loi-de-finances-pour-2026/
- Loi de finances 2017 (FAOLEX) : https://faolex.fao.org/docs/pdf/gab207546.pdf
- Business Consulting Gabon, calendrier des obligations fiscales et sociales (janvier 2022) : https://www.businessconsulting-gabon.com/wp-content/uploads/2022/01/CALENDRIER-DES-OBLIGATIONS-FISCALES-ET-SOCIALES-DU-MOIS-DE-JANVIER-2022.pdf
- Impôts & taxes Gabon (impots-et-taxes.com) : pages IRPP, retenues à la source, IS
- Direct Infos Gabon, « CNAMGS : déclaration des cotisations du 3e trimestre 2026 » : https://directinfosgabon.com/cnamgs-les-entreprises-appelees-a-declarer-leurs-cotisations-du-3e-trimestre-2026/
- Gabonmediatime, « Gabon : le SMIG, bel et bien à 80 000 FCFA en 2026 » : https://gabonmediatime.com/gabon-le-smig-bel-et-bien-a-80-000-fcfa-en-2026/

Sources non accessibles depuis la session (délai de connexion) : dgi.ga (CGI 2022 consolidé, récapitulatif DAS), cnss.ga (procédure DTS), cnlcei.ga. Les consulter en priorité pour lever les points 3 à 10.
