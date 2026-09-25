from . import models


def _post_init_hook(env):
    """Sociétés déjà équipées du plan « ga » : retenues, groupe de taxes et positions fiscales (D-95, D-96)."""
    companies = env['res.company'].search([('chart_template', '=', 'ga'), ('parent_id', '=', False)])
    env['account.chart.template']._l10n_ga_load_withholding(companies)
