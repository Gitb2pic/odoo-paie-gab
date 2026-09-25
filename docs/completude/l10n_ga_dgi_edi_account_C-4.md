# Complétude C-4 — module `l10n_ga_dgi_edi_account` (périmètre V1.0)

Date : 25/09/2026 — prompt `99_completude.md` ; base : rapport de l'étape 5 (`l10n_ga_dgi_edi_account.md`).

## Score

**23 / 24 éléments attendus présents et testés (96 %)** — 8 manques relevés et corrigés ; seul reste le branchement des gabarits `.xlsm` de la V1 (D-87, bloquant externe). 22 tests du module sur base neuve et en mise à jour ; **322 tests** verts avec les quatre modules Gabon ; aucun élément V2.0.

## Manques relevés et corrigés

| # | Manque (source) | Correction | Test |
|---|---|---|---|
| 1 | Arborescence `06` §1 : `generators/id18.py`, `id27.py`, `id23.py`, `id24.py`, `id26.py` (regroupés en 2 fichiers) | un fichier par imprimé ; bases communes `withholding.py`, `fees.py`, `payments.py` | tous |
| 2 | Contrainte anti-double retenue sur les lignes de retenue du **paiement** non testée | test : 9,5 % + 20 % saisis dans l'assistant → refus | `test_payment_withholding_lines_never_cumulate` |
| 3 | Contrôle `GA_RAS_DOUBLE` non testé | tiers reclassé non-résident en cours de mois → anomalie bloquante sur l'ID18 et l'ID27 | `test_double_withholding_detected_after_reclassification` |
| 4 | Débordement de l'ID27 (feuille copiée) non testé | 11 non-résidents → « Bordereau 1 (2) », totaux par feuille, lignes vides nettoyées | `test_id27_overflow_copies_sheet` |
| 5 | Paiement en devise (conversion en FCFA) non testé | 1 000 EUR à 655,957 → base 655 957, retenue 131 191 | `test_foreign_currency_payment` |
| 6 | Sommes versées HT d'une facture avec TVA non testées | 300 000 HT + TVA 18 % → 300 000 versés (pas 354 000) | `test_annual_paid_amounts_excluding_vat_and_refunds` |
| 7 | Avoir dans une annexe annuelle non testé | 100 000 − avoir 20 000 → ID26 : 80 000 versés, 7 600 retenus | idem |
| 8 | Préparation de l'ID18 / l'ID27 par le cron non testée | cron au 06/10 → ID18 et ID27 de septembre calculées, échéance 15/10 | `test_cron_prepares_monthly_declarations` |

## Inventaire final (par imprimé)

| Imprimé | Type | Cases | Générateur | Excel | PDF | Contrôles | Tests |
|---|---|---|---|---|---|---|---|
| ID18 | ✔ mensuel, 15 M+1 | ✔ 13 (cellules du gabarit) | ✔ `id18.py` | ✔ gabarit officiel, feuillets | ✔ rendu du gabarit | ✔ NIF, non classé, retenue absente, double | ✔ 9 |
| ID27 | ✔ | ✔ 13 | ✔ `id27.py` | ✔ gabarit, feuilles copiées | ✔ | ✔ (NIF non exigé) | ✔ 5 |
| ID23 | ✔ annuel, 30/04 | ✔ 6 | ✔ `id23.py` | ✔ classeur neuf | ✔ paysage | ✔ NIF, non classé | ✔ 2 |
| ID24 | ✔ | ✔ 7 | ✔ `id24.py` | ✔ | ✔ | ✔ + Σ ID27 | ✔ 1 |
| ID26 | ✔ | ✔ 6 | ✔ `id26.py` | ✔ | ✔ | ✔ + Σ ID18, retenue absente | ✔ 3 |
| Tiers, taxes, positions, anti-double retenue | — | — | — | — | — | contraintes | ✔ 6 |

Gabarits `.xlsm` V1 des annexes : **absents** (D-87).

## Chasse aux trous (C3)

| Vérification | Résultat |
|---|---|
| TODO / bouchons | aucun (une interface abstraite documentée : `_partner_domain`) |
| Manifeste ↔ fichiers | complet, aucun XML / CSV non déclaré |
| Droits / règles | aucun nouveau modèle ; champs sur modèles standard |
| Nombres en dur | taux portés par les taxes (données, point 09-7) ; aucun dans les générateurs |
| Syntaxe pré-19 | aucune |
| Messages traduisibles | `self.env._` partout ; `i18n` à jour |
| Éléments V2.0 | aucun (recherche CA01, ID30, ID09, ID31, ID01-03, patente, CFU) |
| Points 🔒 | sprint 0 points 7 et 14 confirmés ; constat Odoo 19 (paiement sans écriture avant rapprochement) documenté |
| Hypothèses 09 | point 7 (20 / 25 %) : taux modifiable sur la taxe (D-103) |

## Exécution (C4)

| Commande | Résultat |
|---|---|
| `make lint` | 0 erreur |
| `make test MODULE=l10n_ga_dgi_edi_account` | 22 tests, 0 échec |
| `make upgrade MODULE=l10n_ga_dgi_edi_account` | 22 tests, 0 échec |
| paie + comptabilité de paie + déclarations + comptabilité | 322 tests, 0 échec |

## Constat hors module (à signaler)

Le plan standard `l10n_ga` livre ses TVA d'achat en taxes **groupées** (« 18 % TVA + 1 % CSS ») dont les composantes (`tva_purchase_18`, `css_purchase_1`) sont **inactives** : sur une société de test, une facture avec `tva_purchase_19` ne calcule aucune taxe. Sans effet sur les retenues (calculées sur le HT) ; à vérifier dans la configuration fiscale de la base réelle.

## Bloquants et questions pour Alex

- D-87 : gabarits `.xlsm` de la V1 (annexes ID23 / ID26, DAS).
- D-103 : taux non-résidents 20 % ou 25 %.
- D-74 : cellule du NIF sur les gabarits.

## Dette acceptée

- Facture soldée par un avoir sans paiement : hors sommes versées.
- Plan `ga_syscebnl` sans retenues (compte 4478 absent).
