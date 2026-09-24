# Environnement du VPS

Relevé le 24/09/2026 (sprint 0), en lecture seule. **Aucun mot de passe ici** : ils restent dans `odoo.conf`, hors dépôt.

## Serveur

| Élément | Valeur |
|---|---|
| Hôte | VPS Ubuntu `ubuntu@164.132.106.87` — 3,7 Go RAM, 38 Go disque |
| Service | systemd `odoo19.service` (`/etc/systemd/system/odoo19.service`), `Restart=on-failure`, `KillMode=mixed` |
| Utilisateur système | `ubuntu` (groupe `ubuntu`) |
| Commande du service | `/home/ubuntu/odoo/venv-odoo-19.0/bin/python3 /home/ubuntu/odoo/odoo/odoo-bin -c /home/ubuntu/odoo/odoo/debian/odoo.conf` |
| Fichier de configuration | `/home/ubuntu/odoo/odoo/debian/odoo.conf` |
| Port HTTP production | 8069 (défaut, non surchargé dans `odoo.conf`) |
| Version Odoo | 19.0 FINAL (`odoo/release.py` : `version_info = (19, 0, 0, FINAL, 0, '')`) |
| Community (`$ODOO_PATH`) | `/home/ubuntu/odoo/odoo` — commit `2e2acfd6d272` (24/09/2026) ; addons dans `/home/ubuntu/odoo/odoo/addons` |
| Enterprise (`$ENTERPRISE_PATH`) | `/home/ubuntu/odoo/enterprise` — commit `35b391595918` (24/09/2026) |
| Python / virtualenv Odoo | Python 3.14.4, `/home/ubuntu/odoo/venv-odoo-19.0` (ne pas y installer d'outils de dev) |
| `addons_path` | `/home/ubuntu/odoo/enterprise,/home/ubuntu/odoo/odoo/addons,/home/ubuntu/odoo/extra-addon` |
| PostgreSQL | local (socket), rôle `ubuntu` avec droit `CREATEDB` ; bases existantes `odoo19` (créée par Alex : `hr`, `hr_payroll`, `hr_payroll_holidays`, `hr_payroll_planning` installés, 1 société, 1 salarié, 0 bulletin, sans comptabilité ni `l10n_ga` — relevé le 24/09/2026) et `postgres` — **jamais modifiées** |

## Dépôt `extra-addon`

- Présent dans l'`addons_path` ✔ — mais **ignoré tant qu'il ne contient aucun module** : Odoo journalise `option addons_path, invalid addons directory '/home/ubuntu/odoo/extra-addon', skipped` (constaté au sprint 0). Il devient valide dès le premier module (étape 2.2). Le service de production, démarré avant, devra être **redémarré** (`make restart`) pour voir les nouveaux modules ; les tests (`make test`) relisent l'`addons_path` à chaque lancement et n'en ont pas besoin.
- Contenu au sprint 0 : `CLAUDE.md`, `docs/`, `prompts/`, `.claude/` — aucun module tiers à exclure.
- L'arborescence du fichier `06` §1 nomme le dépôt `odoo-ga-payroll/` : ici c'est `extra-addon/`, modules à la racine (sans impact).
- Outils de dev : virtualenv séparé `.venv/` (Python 3.14, non versionné) : `ruff`, `pytest`, `pytest-cov`, `pre-commit`, `pylint-odoo`, `pyyaml`, et pour l'analyse statique des imports du module : `openpyxl==3.1.2`, `XlsxWriter==3.1.9`, `python-dateutil==2.8.2` (versions du venv Odoo, étape 2.6).

## Commandes utiles

```bash
sudo systemctl restart odoo19        # ou : make restart
sudo systemctl status odoo19
journalctl -u odoo19 -f              # ou : make logs
make test MODULE=<module>            # base neuve test_ga_<module>_<horodatage>, port libre, supprimée à la fin
make upgrade MODULE=<module>         # installation puis -u sur base neuve test_ga_*
make shell DB=test_ga_...            # odoo-bin shell (base de test uniquement)
make demo MODULE=l10n_ga_...         # base de démo odoo19 (D-09) : -i ou -u puis redémarrage du service
```

## Règles d'exploitation

- Bases de test : préfixe obligatoire `test_ga_` (garde-fou dans le `Makefile`) ; filestore `~/.local/share/Odoo/filestore/<base>` supprimé avec la base.
- Les tests tournent sur un port HTTP libre distinct de 8069, avec `--stop-after-init` : le service de production n'est jamais arrêté.
- RAM limitée (~2 Go disponibles) : un seul test Odoo à la fois.
- Le service de production n'a pas de `db_name` : ses crons parcourent toutes les bases du rôle `ubuntu`, **y compris les bases de test** (connexions constatées). Le script de test supprime donc la base avec `dropdb --force`. Correctif recommandé côté production (`db_name = odoo19`) : décision D-04 de `docs/decisions/ouvertes.md`.
- `make test` échoue si le module est introuvable, si aucun test ne tourne, si `odoo-bin` rend un code non nul ou si le journal contient une ligne `ERROR`/`CRITICAL`. Journaux dans `.test-logs/` (non versionné).
- `make upgrade` : installation, puis `-u` avec les seuls tests `post_install` (convention du projet ; les tests `at_install` tournent sur un registre partiel pendant `-u`).
- Avertissements normaux au démarrage des tests : `db_host`/`db_port`/`db_password` à `False` dans `odoo.conf`, `http_interface` absent, dossier `extra-addon` vide (voir plus haut).
