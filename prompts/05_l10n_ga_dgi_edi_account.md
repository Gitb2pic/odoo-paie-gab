# Prompt 05 — Module `l10n_ga_dgi_edi_account` (périmètre V1.0)

---

Tu développes le module `l10n_ga_dgi_edi_account` (dépend de `l10n_ga_dgi_edi`, `l10n_ga`, `l10n_account_withholding_tax`), **périmètre V1.0 uniquement** : classement des bénéficiaires, retenues 9,5 % et 20 %, ID18, ID27, annexes DAS ID23, ID24, ID26. CA01, ID30, ID09, ID31, IS, patente, CFU = V2.0, **hors périmètre** (ne crée ni fichier vide ni bouchon pour eux).

Relis `CLAUDE.md`, `docs/PROGRESS.md`, sprint 0 points 7 et 14 (`l10n_account_withholding_tax` : modèle, multi-paiements, avoirs). Architecture : `05` §5 ; `08` F9 ; `03` RG27 ; `00` ADR-09, ADR-13. Base : `07_autres_impots_entreprise.md`, `06` (DAS), `09` points 7 (20 % vs 25 %) et 9. Classeurs : `ID18_RAS_9.5pct.xlsx`, `ID27_RAS_20pct.xlsx`, `Fichier_DAS - v3.xlsx` (onglets ID23/24/26 — **ne pas reprendre ses formules**, 9 anomalies connues).

Plan dans `docs/plans/5.md`, attente de mon « go », TDD.

## Livrables

- `models/res_partner.py` : `l10n_ga_fee_category` (A administrateurs/commissaires, B courtiers/intermédiaires, C honoraires ; + loyers, prestations si besoin), `l10n_ga_is_resident`, `l10n_ga_zone` (CEMAC / hors CEMAC), `l10n_ga_vat_subject` ; position fiscale automatique selon résidence et assujettissement.
- Taxes de retenue `l10n_ga_ras_095` et `l10n_ga_ras_20` par société (taux en données, 20 % paramétrable — point 09-7), appliquées au paiement via `l10n_account_withholding_tax` ; à défaut (constaté au sprint 0), taxes négatives sur facture — **ADR obligatoire** dans ce cas.
- Règle anti-double retenue : un non-résident ne subit que 20 %, jamais 9,5 % en plus (contrainte + contrôle).
- Générateurs `generators/id18.py`, `id27.py` (mensuels : retenues du mois par bénéficiaire, lues dans les écritures), `id23.py`, `id24.py`, `id26.py` (annuels : lignes de factures fournisseurs payées dans l'année par classement + retenues) enregistrés dans le registre du moteur ; types et cases en données ; rendus Excel/xlsm et PDF ; détails avec `move_line_ids`.
- Contrôles : bénéficiaire non classé, NIF manquant, retenue absente sur un fournisseur classé, double retenue.

## Tests

ID18 et ID27 sur un mois (facture, paiement partiel, deux paiements, avoir) ; non-résident → 20 % seul ; ID23/24/26 sur une année ; cohérence ID26 ↔ Σ ID18 ; multi-société.

## Fin obligatoire

Protocole de complétude `CLAUDE.md` §7 (C1 : chaque imprimé V1.0 = type, cases, générateur, rendu, contrôles, tests ; vérifier qu'**aucun** élément V2.0 n'a été ajouté) ; rapport `docs/completude/l10n_ga_dgi_edi_account.md` ; commit ; `docs/PROGRESS.md` ; attends mon « go ».
