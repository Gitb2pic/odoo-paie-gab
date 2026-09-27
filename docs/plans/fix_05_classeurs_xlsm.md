# FIX 05 — Classeurs officiels « edi-annexe » de la DGI (.xlsm) — D-87 soldé

Go d'Alex (27/09/2026 : « lance les xlsm »). Gabarits DGI récupérés de la V1 (`~/supergel-compta`, D-110) :
`l10n_ga_dgi_edi/static/templates/edi-annexe-ID19.xlsm`, `ID21` ; `l10n_ga_dgi_edi_account/static/templates/
edi-annexe-ID23.xlsm`, `ID26` (ID24 : aucun classeur officiel, classeur neuf conservé).

## Constat
`openpyxl` (utilisé par la V1) perd, en réenregistrant ces classeurs, les dessins de la feuille SAISIE (boutons
de la macro, image), les listes déroulantes étendues (x14), les propriétés personnalisées. D'où un écrivain
XML (`renderers/xlsm_saisie.py`) : seule la feuille SAISIE (et `styles.xml`, `workbook.xml` pour le format date
et le recalcul à l'ouverture) est modifiée ; toutes les autres parties sont recopiées octet pour octet.

## Remplissage (valeurs uniquement, formules du classeur jamais écrasées)
- En-tête : C9 NIF de la société, C11 exercice, C13 « Annuel ».
- ID21 (ligne 18+) : une ligne par salarié, colonnes B à W depuis le détail figé de la DAS (colonnes (1) à (11)
  sauf CFP, absente de l'imprimé) ; libellés des listes du classeur (nationalité, sexe, situation).
- ID19 (ligne 18+) : une ligne par salarié ID19 et par nature : présence = (1) + (4) (le classeur n'a pas de
  nature « indemnités imposables »), congés (5), logement / eau-électricité / domesticité (ventilés depuis
  GA_AN_LOGT / GA_AN_EAU / GA_AN_DOM ; reste des cumuls d'ouverture au logement), nourriture (3), TCS (7),
  IRPP (8), indemnités non imposables. Avantages en nature : V = avantage / taux (paramètre daté), le classeur
  recalcule AG = V × taux = avantage déclaré. Situation « marié » = communauté de biens par défaut (D-113).
- ID23 (ligne 17+) : nom, NIF, profession, nature de la qualité (libellé), sommes versées.
- ID26 (ligne 18+) : nom et adresse, NIF, montant versé ; retenue calculée par le classeur (E = D × 9,5 %).

## Livraison
Joints à l'instantané de validation (`<NIF>-<IDxx>-<exercice>.xlsm`) ; bouton « Classeurs DGI (.xlsm) » (ZIP
pour la DAS). Contrôles : capacité du classeur (avertissement), BP / ville du salarié ID19 (avertissement).
