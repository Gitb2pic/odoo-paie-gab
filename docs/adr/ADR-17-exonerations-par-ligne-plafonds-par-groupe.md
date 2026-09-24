# ADR-17 — Exonérations par ligne, plafonds par groupe (registres `SOCIAL_CAPS` / `TAX_CAPS`)

- **Statut** : proposé (sprint 0, 24/09/2026) — à valider par Alex
- **Origine** : `CLAUDE.md` §3 règle 7 cite ADR-17, absent de `docs/architecture/00_INDEX` (voir `docs/decisions/ouvertes.md` D-02). Rédigé à partir de cette règle ; détail des plafonds dans `docs/base_connaissance/05_elements_de_remuneration.md` et `04_impots_sur_salaires_*.md`.

## Contexte

Certaines rubriques sont exonérées totalement (hors assiette), d'autres partiellement dans la limite d'un **plafond commun à plusieurs rubriques** (ex. : avantages en nature, indemnités de transport/représentation, gratifications dans la limite d'un cumul annuel). Calculer l'exonération rubrique par rubrique donne un résultat faux dès que deux rubriques partagent un plafond ; un calcul global sans détail empêche de justifier la base sur le bulletin et dans la DAS.

## Décision

1. **Dans le noyau** `ga_fiscal_core` (pur, sans `odoo`) : chaque ligne de gain arrive avec son montant et deux **codes de groupe** (social, fiscal) : `None` = imposable, `'EXEMPT'` = exonérée totalement, ou un code de groupe plafonné.
2. Deux **registres** (dicts immuables) `SOCIAL_CAPS` et `TAX_CAPS` : code de groupe → fonction pure `(montants du groupe, FiscalParams, faits du bulletin) → part exonérée`. Les montants de plafond viennent **uniquement** de `FiscalParams` (paramètres datés, règle d'or 1).
3. L'exonération est **répartie sur les lignes** du groupe (au prorata, arrondi au franc sur la dernière ligne pour conserver le total) afin que chaque ligne du bulletin porte sa part imposable et sa part exonérée (bulletin figé F7, colonnes DAS).
4. Côté Odoo, les codes de groupe sont des **champs de la règle salariale** (`l10n_ga_social_group`, `l10n_ga_tax_group`), pas du code dans `amount_python_compute`.
5. Ajouter un plafond = une entrée de registre + un paramètre daté + un test ; aucune autre modification.

## Conséquences

- Test noyau par groupe (sous le plafond, au plafond, au-dessus, plusieurs lignes, répartition des arrondis).
- Couverture ≥ 90 % du noyau inchangée.
- Les points non tranchés du fichier `09` (ex. traitement d'un plafond annuel en cas d'entrée en cours d'année) deviennent des paramètres ou options société (règle d'or 13).

## Alternatives écartées

- Plafond par rubrique : faux pour les plafonds partagés.
- Règles salariales « d'exonération » intermédiaires : logique fiscale dispersée dans les données, non testable sans Odoo (contraire à ADR-03).
