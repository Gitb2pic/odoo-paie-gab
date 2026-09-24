"""Cotisations sociales CNSS et CNAMGS (base de connaissance, fichier 03)."""

from dataclasses import dataclass

from .rounding import round_fcfa


@dataclass(frozen=True)
class SocialContributions:
    cnss_employee: int
    cnamgs_employee: int
    cnss_employer_pf: int
    cnss_employer_at: int
    cnss_employer_avid: int
    cnamgs_employer: int

    @property
    def cnss_employer(self):
        return self.cnss_employer_pf + self.cnss_employer_at + self.cnss_employer_avid


def social_base(subject_gains, presence_ratio, p):
    """Assiette sociale : gains soumis, au moins le SMIG proratisé à la présence.

    Décret 599 art. 34 : l'assiette ne peut être inférieure au SMIG.
    """
    if not 0 <= presence_ratio <= 1:
        raise ValueError(f'Taux de présence hors de [0, 1] : {presence_ratio}')
    return max(round_fcfa(p.smig * presence_ratio), round_fcfa(subject_gains))


def social_contributions(base, p):
    """Parts salariales et patronales, chacune arrondie au franc sur son plafond."""
    cnss_base = min(base, p.cnss_ceiling)
    cnamgs_base = min(base, p.cnamgs_ceiling)
    return SocialContributions(
        cnss_employee=round_fcfa(cnss_base * p.cnss_employee_rate),
        cnamgs_employee=round_fcfa(cnamgs_base * p.cnamgs_employee_rate),
        cnss_employer_pf=round_fcfa(cnss_base * p.cnss_employer_pf_rate),
        cnss_employer_at=round_fcfa(cnss_base * p.cnss_employer_at_rate),
        cnss_employer_avid=round_fcfa(cnss_base * p.cnss_employer_avid_rate),
        cnamgs_employer=round_fcfa(cnamgs_base * p.cnamgs_employer_rate),
    )
