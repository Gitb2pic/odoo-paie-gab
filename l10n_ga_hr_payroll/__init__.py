from . import models, wizard


def _post_init_hook(env):
    """Parts et code nationalité des versions existantes : calculés avant le chargement des paramètres."""
    versions = env['hr.version'].with_context(active_test=False).search([])
    versions._compute_l10n_ga_tax_parts()
    versions._compute_l10n_ga_nationality_code()
    # D-111 : convention « Tronc commun » par défaut de chaque société gabonaise
    env['res.company'].search([])._l10n_ga_ensure_default_agreement()
