# ADR-20 — Vue ID10 et imprimés PDF au format de la V1

- Statut : **accepté** (Alex, 26/09/2026 : « reprends la vue de l'ID10, son report et les reports des autres ID »)
- Remplace partiellement : décision 4.1 « PDF = rendu fidèle du classeur » (report_declaration).

## Contexte
La V2 imprime chaque déclaration en rendant son classeur Excel en HTML. Alex préfère la présentation de la
V1 (`~/supergel-compta/l10n_ga_dgi_edi`, formulaire ID10 par cadres, imprimés QWeb fac-similés).

## Décision
1. Les PDF des imprimés sont des gabarits QWeb au format V1, **réécrits** pour le modèle V2 (aucun champ V1) :
   ils lisent uniquement les cases (`l10n_ga.declaration.line`) et détails figés ; aucun calcul dans le gabarit
   hormis sommes d'affichage de détails déjà stockés.
2. Le `report_id` de chaque type pointe sur son gabarit V1 ; l'instantané de validation joint donc ce PDF.
3. Le rendu « classeur » reste un rapport secondaire (contrôle visuel du `.xlsx` / `.xlsm`).
4. L'ID10 a un formulaire dédié (cadres 1 à 4) ; ses montants sont des champs d'affichage non stockés lus sur
   les cases stockées : la valeur déclarée reste figée (règle d'or 8).

## Conséquences
Deux rendus à maintenir pour un même imprimé ; les tests de rendu PDF vérifient les montants des cases.
