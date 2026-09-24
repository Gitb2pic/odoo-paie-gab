#!/usr/bin/env bash
# Régénère <module>/i18n/<module>.pot et fr.po depuis une base neuve test_ga_* (supprimée ensuite).
#   tools/odoo_i18n.sh <module>
set -uo pipefail

MODULE="${1:?usage: odoo_i18n.sh <module>}"
ODOO_PY="${ODOO_PY:-/home/ubuntu/odoo/venv-odoo-19.0/bin/python3}"
ODOO_BIN="${ODOO_BIN:-/home/ubuntu/odoo/odoo/odoo-bin}"
ODOO_CONF="${ODOO_CONF:-/home/ubuntu/odoo/odoo/debian/odoo.conf}"
DATA_DIR="${ODOO_DATA_DIR:-$HOME/.local/share/Odoo}"

if [[ ! "$MODULE" =~ ^[a-z0-9_]+$ ]]; then
    echo "nom de module invalide : $MODULE" >&2; exit 2
fi
DB="test_ga_i18n_$(date +%Y%m%d%H%M%S)"
cleanup() {
    dropdb --if-exists --force "$DB" || echo "!! suppression de $DB impossible" >&2
    rm -rf "${DATA_DIR:?}/filestore/${DB}"
}
trap cleanup EXIT

"$ODOO_PY" "$ODOO_BIN" -c "$ODOO_CONF" -d "$DB" --db-filter="^${DB}\$" --no-http --without-demo=True \
    --stop-after-init --log-level=warn -i "$MODULE" --load-language=fr_FR || exit 1
"$ODOO_PY" "$ODOO_BIN" i18n export -c "$ODOO_CONF" -d "$DB" "$MODULE" -l pot fr || exit 1
echo ">> $MODULE/i18n régénéré"
