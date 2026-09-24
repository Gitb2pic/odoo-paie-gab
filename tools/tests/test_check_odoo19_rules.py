import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_odoo19_rules as rules


def _write(base, relpath, content):
    path = base / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def test_sql_constraints_detected(tmp_path):
    path = _write(tmp_path, 'm/models/a.py', 'class A:\n    _sql_constraints = []\n')
    assert rules.check_file(path) == [f'{path}:2: _sql_constraints : utiliser models.Constraint']


def test_attrs_and_tree_detected(tmp_path):
    path = _write(tmp_path, 'm/views/v.xml', '<odoo>\n<tree attrs="{}"/>\n</odoo>\n')
    messages = rules.check_file(path)
    assert len(messages) == 2
    assert all(message.startswith(f'{path}:2:') for message in messages)


def test_list_view_and_constraint_accepted(tmp_path):
    xml = _write(tmp_path, 'm/views/v.xml', '<odoo><list invisible="state == \'done\'"/></odoo>\n')
    py = _write(tmp_path, 'm/models/a.py', "_x = models.Constraint('unique(a)', 'msg')\n")
    assert rules.check_file(xml) == []
    assert rules.check_file(py) == []


def test_odoo_import_forbidden_in_core(tmp_path):
    path = _write(
        tmp_path,
        'l10n_ga_hr_payroll/lib/ga_fiscal_core/tax.py',
        'import math\nfrom odoo.tools import float_round\nimport odoo\n',
    )
    assert rules.check_file(path) == [
        f'{path}:2: import odoo.tools interdit dans ga_fiscal_core',
        f'{path}:3: import odoo interdit dans ga_fiscal_core',
    ]


def test_odoo_import_allowed_outside_core(tmp_path):
    path = _write(tmp_path, 'l10n_ga_hr_payroll/models/hr_payslip.py', 'from odoo import models\n')
    assert rules.check_file(path) == []


def test_main_exit_codes(tmp_path, capsys):
    bad = _write(tmp_path, 'm/views/v.xml', '<tree/>\n')
    good = _write(tmp_path, 'm/views/w.xml', '<list/>\n')
    ignored = _write(tmp_path, 'm/data/p.csv', '_sql_constraints\n')
    assert rules.main([str(good), str(ignored)]) == 0
    assert rules.main([str(bad), str(tmp_path / 'absent.xml')]) == 1
    assert '<tree>' in capsys.readouterr().out
