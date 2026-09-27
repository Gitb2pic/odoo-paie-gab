# FIX 04 — Convention collective et grade par défaut (D-111)

Demande d'Alex (27/09/2026) : règles d'ancienneté de la réglementation gabonaise et grades configurés par
défaut à la création d'un salarié, modifiables ensuite.

- Sources : tronc commun des conventions collectives (base 05 §4, confirmé par la source « Fonctionnement des
  primes et indemnités ») : 2 % après 2 ans de présence, +1 % par an, sur le salaire de base conventionnel ;
  plafond propre à chaque convention (absent des sources). Seule grille disponible : Commerce 2012 (5 grades).
- Données : `agreement_example_common` devient « Tronc commun … » (code TRONC_COMMUN, plus « exemple ») ;
  migration 19.0.1.8.0 pour les bases existantes (données noupdate).
- Société gabonaise : convention par défaut assurée (création de société, installation, migration) ; copie
  par société de la convention livrée.
- Version du contrat : convention par défaut recopiée à la création ; grade vide complété avec le plus haut
  grade dont le minimum ≤ salaire (à la date de la version) ; changement de convention = grade re-suggéré ;
  jamais d'écrasement d'un grade choisi.
- Salariés existants : action « Appliquer la convention et le grade par défaut (Gabon) » (liste / fiche).
- Tests : `test_agreement` (7 nouveaux), `test_checks` adapté ; mise à jour réelle depuis 9432d13 : 367 tests.
