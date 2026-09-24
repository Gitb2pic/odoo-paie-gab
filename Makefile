# Commandes du projet Paie Gabon (voir CLAUDE.md §5 et docs/environnement_vps.md).
# Les tests Odoo tournent sur une base neuve test_ga_* et un port libre :
# le service de production odoo19 n'est jamais arrêté.

ODOO_PY   ?= /home/ubuntu/odoo/venv-odoo-19.0/bin/python3
ODOO_BIN  ?= /home/ubuntu/odoo/odoo/odoo-bin
ODOO_CONF ?= /home/ubuntu/odoo/odoo/debian/odoo.conf
VENV      ?= .venv
MODULE    ?=
DB        ?=

export ODOO_PY ODOO_BIN ODOO_CONF

.PHONY: help lint test-core test upgrade demo shell restart logs

help:
	@echo "make lint | test-core | test MODULE=x | upgrade MODULE=x | demo MODULE=x | shell DB=test_ga_x | restart | logs"

lint:
	$(VENV)/bin/pre-commit run --all-files

# Outillage du dépôt (tools/tests, sans seuil de couverture) puis noyau fiscal pur
# (sans Odoo, couverture >= 90 %). Tant que le noyau n'existe pas (sprint 0),
# seule la première partie s'exécute.
test-core:
	$(VENV)/bin/pytest tools/tests --no-cov -p no:cacheprovider
	@if [ -d l10n_ga_hr_payroll/lib ]; then \
		$(VENV)/bin/pytest; \
	else \
		echo ">> l10n_ga_hr_payroll/lib absent : noyau pas encore créé (étape 2.1)"; \
	fi

test:
	@test -n "$(MODULE)" || (echo "usage : make test MODULE=<module>" && exit 2)
	tools/odoo_test.sh test '$(MODULE)'

upgrade:
	@test -n "$(MODULE)" || (echo "usage : make upgrade MODULE=<module>" && exit 2)
	tools/odoo_test.sh upgrade '$(MODULE)'

# Base de démonstration d'Alex (odoo19, décision D-09) : installe ou met à jour
# un module l10n_ga_* validé, sans tests, puis redémarre le service.
demo:
	@test -n "$(MODULE)" || (echo "usage : make demo MODULE=<module>" && exit 2)
	tools/odoo_demo.sh '$(MODULE)'

shell:
	@case "$(DB)" in test_ga_*) ;; *) echo "refus : DB doit commencer par test_ga_" && exit 2 ;; esac
	$(ODOO_PY) $(ODOO_BIN) shell -c $(ODOO_CONF) -d '$(DB)' --no-http

restart:
	sudo systemctl restart odoo19

logs:
	journalctl -u odoo19 -f
