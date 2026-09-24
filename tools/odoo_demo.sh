#!/usr/bin/env bash
# Installe ou met à jour un module Gabon dans la base de démonstration d'Alex
# (odoo19, décision D-09), puis redémarre le service pour qu'il le voie.
#
#   tools/odoo_demo.sh <module>
#
# Seule base autorisée : $DEMO_DB (odoo19). Pas de tests ici : ils tournent sur
# des bases test_ga_* (make test). À lancer uniquement après une étape validée.
set -uo pipefail

MODULE="${1:?usage: odoo_demo.sh <module>}"
DEMO_DB="odoo19"
ODOO_PY="${ODOO_PY:-/home/ubuntu/odoo/venv-odoo-19.0/bin/python3}"
ODOO_BIN="${ODOO_BIN:-/home/ubuntu/odoo/odoo/odoo-bin}"
ODOO_CONF="${ODOO_CONF:-/home/ubuntu/odoo/odoo/debian/odoo.conf}"

if [[ ! "$MODULE" =~ ^l10n_ga_[a-z0-9_]+$ ]]; then
    echo "refus : seuls les modules l10n_ga_* du dépôt vont dans $DEMO_DB ($MODULE)" >&2; exit 2
fi
if [[ ! -f "$(dirname "$0")/../$MODULE/__manifest__.py" ]]; then
    echo "refus : $MODULE absent du dépôt" >&2; exit 2
fi

STATE=$(psql -d "$DEMO_DB" -Atc "SELECT state FROM ir_module_module WHERE name = '$MODULE'")
if [[ "$STATE" == installed ]]; then ACTION=(-u "$MODULE"); else ACTION=(-i "$MODULE"); fi

echo ">> $DEMO_DB : ${ACTION[0]} $MODULE (état actuel : ${STATE:-inconnu})"
"$ODOO_PY" "$ODOO_BIN" -c "$ODOO_CONF" -d "$DEMO_DB" "${ACTION[@]}" \
    --stop-after-init --no-http --without-demo=True
RC=$?
if (( RC != 0 )); then
    echo "!! échec (code $RC) : service non redémarré" >&2; exit "$RC"
fi
# Le service ne voit les nouveaux modules d'extra-addon qu'après redémarrage.
sudo systemctl restart odoo19 && echo ">> service odoo19 redémarré"
