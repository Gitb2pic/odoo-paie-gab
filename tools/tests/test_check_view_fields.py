import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_view_fields as checker

REPO = Path(__file__).resolve().parents[2]
HEADER = 'from odoo import fields, models\n\n\ndef _money(label):\n    return fields.Monetary(string=label)\n\n\n'
CLASS = "class ResCompany(models.Model):\n    _inherit = 'res.company'\n\n"
FIELDS = {
    'selection': "    l10n_ga_entry_exit_hours = fields.Selection([('deduct', 'a')])\n",
    'factory': "    l10n_ga_frozen = _money('Figé')\n",
    'other': '    l10n_ga_autre_modele = fields.Char()\n',
}
VIEW = """<odoo>
    <record id="v" model="ir.ui.view">
        <field name="model">{model}</field>
        <field name="arch" type="xml">
            <form>
                <field name="{field}"/>
                <field name="line_ids"><list><field name="l10n_ga_autre_modele"/></list></field>
            </form>
        </field>
    </record>
</odoo>
"""


def _module(tmp_path, field='l10n_ga_entry_exit_hours', model='res.company', fields=('selection', 'other')):
    module = tmp_path / 'l10n_ga_x'
    (module / 'models').mkdir(parents=True)
    (module / 'views').mkdir()
    source = HEADER + CLASS + ''.join(FIELDS[key] for key in fields)
    (module / 'models' / 'res_company.py').write_text(source, encoding='utf-8')
    (module / 'views' / 'v.xml').write_text(VIEW.format(model=model, field=field), encoding='utf-8')
    return tmp_path


def test_defined_field_accepted(tmp_path):
    assert checker.check(_module(tmp_path)) == []


def test_field_factory_recognised(tmp_path):
    assert checker.check(_module(tmp_path, field='l10n_ga_frozen', fields=('factory', 'other'))) == []


def test_misspelled_field_detected(tmp_path):
    errors = checker.check(_module(tmp_path, field='l10n_ga_entry_exit_hour'))
    assert len(errors) == 1
    assert 'l10n_ga_entry_exit_hour' in errors[0]
    assert 'res.company' in errors[0]


def test_field_on_other_model_detected(tmp_path):
    errors = checker.check(_module(tmp_path, model='hr.version'))
    assert len(errors) == 1
    assert 'hr.version' in errors[0]


def test_standard_fields_ignored_and_sub_view_checked_loosely(tmp_path):
    # « name » : champ d'Odoo, hors du dépôt, non contrôlé ; la sous-vue vise un modèle lié inconnu.
    errors = checker.check(_module(tmp_path, field='name', fields=('selection',)))
    assert len(errors) == 1
    assert 'aucun modèle' in errors[0]


def test_repository_views_are_consistent():
    assert checker.check(REPO) == []
