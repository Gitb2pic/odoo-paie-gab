"""Mise en page du bulletin imprimé (modèle fourni par Alex, plan 2.7 b, D-54, D-55).

Le code d'impression numérique (``print_code`` du catalogue) ordonne les lignes et fixe leur
section. Les parts salariale et patronales d'un même organisme partagent un code : elles sont
imprimées sur la même ligne. Les lignes de total et d'information n'existent qu'à l'impression.
"""

GAINS = 'gains'  # gains en espèces imposables → TOTAL BRUT
CONTRIBUTIONS = 'contributions'  # cotisations salariales et patronales → TOTAL COTISATIONS
BENEFITS = 'benefits'  # avantages en nature (non versés)
TAXES = 'taxes'  # TCS, IRPP
ALLOWANCES = 'allowances'  # indemnités exonérées ou partiellement exonérées
DEDUCTIONS = 'deductions'  # autres retenues (avance, prêt, cession, saisie)
PAY = 'pay'  # net, arrondi espèces, net à payer

SECTIONS = (
    (10000, 19999, GAINS),
    (25000, 26999, CONTRIBUTIONS),
    (30000, 30999, BENEFITS),
    (31000, 32999, TAXES),
    (34000, 34999, ALLOWANCES),
    (40000, 49999, DEDUCTIONS),
    (80000, 89999, PAY),
)

# Lignes calculées à l'impression (jamais des règles).
ABSENCE = 10050
TOTAL_GROSS = 20900
TOTAL_CONTRIBUTIONS = 26990
TOTAL_BENEFITS = 30200
TCS_BASE = 31490
TOTAL_GAINS = 70000
TOTAL_DEDUCTIONS = 75000
VIRTUAL_CODES = frozenset(
    {ABSENCE, TOTAL_GROSS, TOTAL_CONTRIBUTIONS, TOTAL_BENEFITS, TCS_BASE, TOTAL_GAINS, TOTAL_DEDUCTIONS}
)


def section(code):
    """Section d'un code d'impression ; ``ValueError`` hors des plages."""
    number = int(code)
    for low, high, name in SECTIONS:
        if low <= number <= high:
            return name
    raise ValueError(f'Code d’impression hors section : {code!r}')
