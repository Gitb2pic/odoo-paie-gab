"""Traitement social et fiscal d'une rubrique (ADR-17, F6, décision D-16).

Chaque rubrique porte une assiette sociale et une assiette fiscale :

- sociale : ``subject`` (soumise), ``excluded`` (exclue en totalité, groupe ``EXCLUDED``),
  ``capped`` (exclue dans la limite d'un groupe de ``SOCIAL_CAPS``), ``none`` (retenues,
  totaux, charges : hors assiette) ;
- fiscale : ``taxable``, ``exempt`` (groupe ``EXEMPT``), ``capped`` (groupe de ``TAX_CAPS``),
  ``none``.

Le vocabulaire est partagé par le catalogue ``data/catalogue_rubriques_ga.csv`` (générateur),
les champs de ``hr.salary.rule`` et l'adaptateur (étape 2.3), qui traduit l'assiette en
groupe de ``GainLine`` par ``social_group`` / ``tax_group``.
"""

from .exemptions import SOCIAL_CAPS, TAX_CAPS

CAPPED = 'capped'
NONE = 'none'
SOCIAL_BASES = ('subject', 'excluded', CAPPED, NONE)
TAX_BASES = ('taxable', 'exempt', CAPPED, NONE)

# Colonnes de la DAS (base 06 §3.1) : partie imposable et partie exonérée d'une rubrique.
DAS_COLUMNS = (
    'presence',  # (1) salaire brut de présence
    'benefit',  # (2) avantages en nature logement, eau et électricité, domesticité
    'food',  # (3) nourriture
    'taxable_allowance',  # (4) indemnités imposables
    'leave',  # (5) salaire brut de congé
    'nt_housing',  # indemnités non imposables : logement
    'nt_transport',  # transport
    'nt_domestic',  # domesticité, gaz
    'nt_other',  # autres
    NONE,
)

_TOTAL_GROUPS = {'social': ('excluded', 'EXCLUDED'), 'tax': ('exempt', 'EXEMPT')}


def _group(kind, base, group):
    total_base, total_group = _TOTAL_GROUPS[kind]
    if base == total_base:
        return total_group
    if base == CAPPED:
        return group
    return None


def social_group(base, group):
    """Groupe ``GainLine.social_group`` d'une rubrique (``None`` = soumise ou hors assiette)."""
    return _group('social', base, group)


def tax_group(base, group):
    """Groupe ``GainLine.tax_group`` d'une rubrique (``None`` = imposable ou hors assiette)."""
    return _group('tax', base, group)


def _check_side(code, label, base, group, bases, registry, total_group):
    if base not in bases:
        raise ValueError(f'{code} : assiette {label} invalide {base!r} (attendu : {", ".join(bases)})')
    if base == CAPPED:
        if not group:
            raise ValueError(f'{code} : assiette {label} plafonnée sans groupe de plafond')
        if group == total_group:
            raise ValueError(f'{code} : le groupe {group} est un traitement total, pas un plafond')
        if group not in registry:
            raise ValueError(f'{code} : groupe {label} inconnu du noyau {group!r}')
    elif group:
        raise ValueError(f'{code} : groupe {group!r} renseigné sur une assiette {label} non plafonnée')


def check_treatment(code, social_base, social_cap_group, tax_base, tax_cap_group):
    """Lève ``ValueError`` si le traitement est incohérent (message en français, code en tête)."""
    _check_side(code, 'sociale', social_base, social_cap_group, SOCIAL_BASES, SOCIAL_CAPS, 'EXCLUDED')
    _check_side(code, 'fiscale', tax_base, tax_cap_group, TAX_BASES, TAX_CAPS, 'EXEMPT')
    if (social_base == NONE) != (tax_base == NONE):
        raise ValueError(f'{code} : assiettes sociale et fiscale doivent être toutes deux « none » ou aucune')
