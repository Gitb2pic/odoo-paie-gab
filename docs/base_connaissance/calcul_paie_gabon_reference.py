"""
Calcul de référence de la paie Gabon (2026) — implémentation "papier" destinée
à valider les règles salariales de l'addon Odoo (tests unitaires / recette).

Hypothèses (voir 09_points_a_verifier.md) :
  - CNSS 2026 (décret 0487/PR/MASI) : salarié 5 %, employeur 18 % (PF 5 + AT 2 + AVID 11), plafond 1 500 000/mois
  - CNAMGS : salarié 2 %, employeur 4,1 %, plafond 2 500 000/mois
  - TCS : 5 % sur (brut imposable - CNSS sal - CNAMGS sal - 150 000) si positif
  - IRPP : base mensuelle = brut imposable - CNSS sal - CNAMGS sal - TCS ; annualisée x12 ;
           abattement 20 % plafonné 10 000 000/an ; quotient familial ; barème art. 174 CGI
  - FNH : 3 % employeur (LFR 2026, loi 002/2026) sur assiette CNSS plafonnée
  - CFP : 0,5 % employeur sur brut (y.c. avantages) plafonné 1 500 000/mois
Tous les montants sont en FCFA, arrondis à l'unité.
"""
from dataclasses import dataclass

PARAMS = {
    "cnss_sal": 0.05, "cnss_pat": 0.18, "cnss_plafond": 1_500_000,
    "cnamgs_sal": 0.02, "cnamgs_pat": 0.041, "cnamgs_plafond": 2_500_000,
    "tcs_taux": 0.05, "tcs_exo_mensuel": 150_000,
    "abattement_fp_taux": 0.20, "abattement_fp_plafond_annuel": 10_000_000,
    "fnh_taux": 0.03, "fnh_plafond": 1_500_000,
    "cfp_taux": 0.005, "cfp_plafond": 1_500_000,
    "tcs_deduit_cnamgs": True,
}

# Barème IRPP annuel pour 1 part : (borne_inf, borne_sup, taux, constante N)  impôt = taux*Q - N
BAREME = [
    (0, 1_500_000, 0.00, 0),
    (1_500_001, 1_920_000, 0.05, 75_000),
    (1_920_001, 2_700_000, 0.10, 171_000),
    (2_700_001, 3_600_000, 0.15, 306_000),
    (3_600_001, 5_160_000, 0.20, 486_000),
    (5_160_001, 7_500_000, 0.25, 744_000),
    (7_500_001, 11_000_000, 0.30, 1_119_000),
    (11_000_001, float("inf"), 0.35, 1_669_000),
]


def nombre_parts(situation: str, enfants: int, enfants_infirmes: int = 0) -> float:
    """situation: 'celibataire' | 'divorce' | 'veuf' | 'marie'. Max 6 enfants comptés.
    Célibataire/divorcé : 1 part, +1 pour le 1er enfant, +0,5 par enfant suivant.
    Marié (ou veuf avec enfants) : 2 parts + 0,5 par enfant. Enfant infirme : 1 part au lieu de 0,5."""
    n = min(enfants, 6)
    inf = min(enfants_infirmes, n)
    if situation == "marie" or (situation == "veuf" and n > 0):
        parts = 2 + 0.5 * n
    else:
        parts = 1 + (1 + 0.5 * (n - 1) if n > 0 else 0)
    return parts + 0.5 * inf


def impot_une_part(q: float) -> float:
    for lo, hi, t, n in BAREME:
        if q <= hi:
            return max(0.0, t * q - n)
    raise ValueError


def irpp_annuel(rni_annuel: float, parts: float) -> float:
    q = rni_annuel / parts
    return impot_une_part(q) * parts


@dataclass
class Bulletin:
    gains_total: float          # total des gains du mois (base, HS, primes, indemnités, AN valorisés)
    exo_social: float = 0       # part exclue de l'assiette CNSS/CNAMGS (arrêté 016/MTEPS : frais pro, transport <= 35 000...)
    exo_fiscal: float = 0       # part exonérée d'IRPP/TCS (art. 91, 91 bis, gratifications <= 4 M/an...)
    situation: str = "celibataire"
    enfants: int = 0
    p: dict = None

    def calcul(self):
        p = self.p or PARAMS
        r = {}
        assiette = self.gains_total - self.exo_social
        brut_imposable = self.gains_total - self.exo_fiscal
        a_cnss = min(assiette, p["cnss_plafond"])
        a_cnam = min(assiette, p["cnamgs_plafond"])
        r["assiette_sociale"] = assiette
        r["brut_imposable"] = brut_imposable
        r["cnss_sal"] = round(a_cnss * p["cnss_sal"])
        r["cnamgs_sal"] = round(a_cnam * p["cnamgs_sal"])
        ded_soc = r["cnss_sal"] + (r["cnamgs_sal"] if p["tcs_deduit_cnamgs"] else 0)
        base_tcs = brut_imposable - ded_soc
        r["base_tcs"] = base_tcs
        r["tcs"] = round(max(0, base_tcs - p["tcs_exo_mensuel"]) * p["tcs_taux"])
        base_irpp_m = base_tcs - r["tcs"]
        annuel = base_irpp_m * 12
        abatt = min(annuel * p["abattement_fp_taux"], p["abattement_fp_plafond_annuel"])
        rni = annuel - abatt
        parts = nombre_parts(self.situation, self.enfants)
        r["parts"] = parts
        r["rni_annuel"] = round(rni)
        r["quotient"] = round(rni / parts)
        r["irpp"] = round(irpp_annuel(rni, parts) / 12)
        r["total_retenues"] = r["cnss_sal"] + r["cnamgs_sal"] + r["tcs"] + r["irpp"]
        r["net_a_payer"] = round(self.gains_total - r["total_retenues"])
        r["cnss_pat"] = round(a_cnss * p["cnss_pat"])
        r["cnamgs_pat"] = round(a_cnam * p["cnamgs_pat"])
        r["fnh"] = round(min(assiette, p["fnh_plafond"]) * p["fnh_taux"])
        r["cfp"] = round(min(assiette, p["cfp_plafond"]) * p["cfp_taux"])
        r["cout_employeur"] = round(self.gains_total + r["cnss_pat"] + r["cnamgs_pat"] + r["fnh"] + r["cfp"])
        return r


if __name__ == "__main__":
    # Tests de parts
    assert nombre_parts("celibataire", 0) == 1
    assert nombre_parts("celibataire", 1) == 2
    assert nombre_parts("celibataire", 2) == 2.5
    assert nombre_parts("celibataire", 4) == 3.5
    assert nombre_parts("marie", 0) == 2
    assert nombre_parts("marie", 3) == 3.5
    assert nombre_parts("marie", 8) == 5
    # Continuité du barème aux bornes
    for i in range(1, len(BAREME)):
        lo = BAREME[i][0] - 1
        a = BAREME[i - 1][2] * lo - BAREME[i - 1][3]
        b = BAREME[i][2] * lo - BAREME[i][3]
        assert abs(a - b) < 1e-6, (lo, a, b)
    # Cas pratique ULYSS 2012 (barème identique) : Q = 4 288 662 -> 15% x Q - 306 000 = 337 299
    assert round(0.15 * 4_288_662 - 306_000) == 337_299
    assert round(impot_une_part(4_288_662)) != 337_299  # Q=4,29M tombe en tranche 20% et non 15% -> erreur du support
    print("impot 1 part Q=4 288 662 (tranche 20%) :", round(impot_une_part(4_288_662)))

    for titre, b in [
        # Ex.1 : données du support "Architecture de la paie 2026" : base 450 000 + ancienneté 45 000
        #        + HS 20 000 + transport 30 000 (transport exclu CNSS <= 35 000 et supposé exonéré IRPP/TCS)
        ("Ex.1 Célibataire, gains 545 000 dont transport 30 000", Bulletin(545_000, 30_000, 30_000, "celibataire", 0)),
        ("Ex.2 Marié 2 enfants, brut 850 000", Bulletin(850_000, 0, 0, "marie", 2)),
        ("Ex.3 Célibataire 1 enfant, brut 2 000 000", Bulletin(2_000_000, 0, 0, "celibataire", 1)),
        ("Ex.4 Marié 3 enfants, brut 5 000 000", Bulletin(5_000_000, 0, 0, "marie", 3)),
    ]:
        print("\n" + titre)
        for k, v in b.calcul().items():
            print(f"   {k:15s} {v:>14,}".replace(",", " "))
