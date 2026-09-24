#!/usr/bin/env bash
# Lance les tests Odoo d'un module sur une base neuve test_ga_*, puis la supprime.
#
#   tools/odoo_test.sh test    <module>   installation + tests (--test-tags /<module>)
#   tools/odoo_test.sh upgrade <module>   installation, puis mise à jour (-u) + tests
#
# Garde-fous : base préfixée test_ga_, port HTTP libre (jamais 8069), le service
# de production n'est jamais arrêté. La base et son filestore sont supprimés même
# en cas d'échec ; le code de sortie reflète tests + erreurs du journal.
set -uo pipefail

MODE="${1:?usage: odoo_test.sh test|upgrade <module>}"
MODULE="${2:?usage: odoo_test.sh test|upgrade <module>}"
ODOO_PY="${ODOO_PY:-/home/ubuntu/odoo/venv-odoo-19.0/bin/python3}"
ODOO_BIN="${ODOO_BIN:-/home/ubuntu/odoo/odoo/odoo-bin}"
ODOO_CONF="${ODOO_CONF:-/home/ubuntu/odoo/odoo/debian/odoo.conf}"
DATA_DIR="${ODOO_DATA_DIR:-$HOME/.local/share/Odoo}"
LOG_DIR="${LOG_DIR:-$(dirname "$0")/../.test-logs}"

case "$MODE" in test|upgrade) ;; *) echo "mode inconnu : $MODE" >&2; exit 2 ;; esac
if [[ ! "$MODULE" =~ ^[a-z0-9_]+$ ]]; then
    echo "nom de module invalide : $MODULE" >&2; exit 2
fi

DB="test_ga_${MODULE}_$(date +%Y%m%d%H%M%S)"
if [[ "$DB" != test_ga_* ]]; then
    echo "refus : la base doit commencer par test_ga_ ($DB)" >&2; exit 2
fi
if (( ${#DB} > 63 )); then
    DB="${DB:0:63}"   # limite PostgreSQL des identifiants
fi

PORT="$("$ODOO_PY" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/${DB}.log"

cleanup() {
    # --force : filet de sécurité si une connexion traîne encore sur la base de test
    # (avant D-04, les crons du service parcouraient toutes les bases du rôle).
    if ! dropdb --if-exists --force "$DB"; then
        echo "!! suppression de $DB impossible : à supprimer à la main" >&2
    fi
    rm -rf "${DATA_DIR:?}/filestore/${DB}"
}
trap cleanup EXIT

# --db-filter : odoo.conf limite le service à odoo19 (dbfilter, D-04) ; le serveur
# de test doit accepter sa propre base pour les tests HttpCase.
COMMON=(-c "$ODOO_CONF" -d "$DB" --db-filter="^${DB}\$" --http-port="$PORT" --without-demo=True
        --stop-after-init --log-level=test --no-database-list)

echo ">> base $DB, port $PORT, journal $LOG"
if [[ "$MODE" == test ]]; then
    "$ODOO_PY" "$ODOO_BIN" "${COMMON[@]}" -i "$MODULE" --test-tags "/$MODULE" 2>&1 | tee "$LOG"
    RC=${PIPESTATUS[0]}
else
    "$ODOO_PY" "$ODOO_BIN" "${COMMON[@]}" -i "$MODULE" 2>&1 | tee "$LOG"
    RC=${PIPESTATUS[0]}
    if (( RC == 0 )); then
        # Après -u, seulement les tests post_install (convention du projet) : les tests
        # at_install tournent sur un registre partiel pendant la mise à jour et peuvent
        # échouer sur des colonnes NOT NULL ajoutées par des modules chargés plus tard.
        "$ODOO_PY" "$ODOO_BIN" "${COMMON[@]}" -u "$MODULE" --test-tags "/$MODULE,-at_install" 2>&1 | tee -a "$LOG"
        RC=${PIPESTATUS[0]}
    fi
fi

ERRORS=$(grep -cE ' (ERROR|CRITICAL) ' "$LOG")
WARNINGS=$(grep -cE ' WARNING ' "$LOG")
# Nombre de tests du dernier passage (« N failed, M error(s) of T tests »)
TESTS=$(grep -oE 'error\(s\) of [0-9]+ tests' "$LOG" | tail -n 1 | grep -oE '[0-9]+')
echo ">> code odoo-bin : $RC — tests : ${TESTS:-0} — lignes ERROR/CRITICAL : $ERRORS — WARNING : $WARNINGS"
if grep -qE "invalid module names, ignored: .*\b${MODULE}\b" "$LOG"; then
    echo "!! module $MODULE introuvable dans l'addons_path" >&2
    exit 1
fi
if (( ${TESTS:-0} == 0 )); then
    echo "!! aucun test exécuté pour /$MODULE" >&2
    exit 1
fi
if (( RC != 0 || ERRORS > 0 )); then
    exit 1
fi
exit 0
