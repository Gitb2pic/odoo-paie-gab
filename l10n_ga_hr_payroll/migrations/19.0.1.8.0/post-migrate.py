"""D-111 : l'ancienne convention « EXEMPLE » devient la convention par défaut « Tronc commun » (données
noupdate : non mises à jour par le chargement du module), puis chaque société gabonaise sans convention par
défaut la reçoit. Les salariés existants ne sont pas modifiés : action « Appliquer la convention et le grade
par défaut (Gabon) » sur la liste des salariés."""

from odoo import SUPERUSER_ID, api

OLD_CODE = 'EXEMPLE'


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    template = env.ref('l10n_ga_hr_payroll.agreement_example_common', raise_if_not_found=False)
    if template and template.code == OLD_CODE:
        template.write(
            {
                'name': 'Tronc commun des conventions collectives (grille Commerce 2012, à actualiser)',
                'code': 'TRONC_COMMUN',
                'is_example': False,
            }
        )
    env['res.company'].search([])._l10n_ga_ensure_default_agreement()
