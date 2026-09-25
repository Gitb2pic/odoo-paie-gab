# Plan — FIX 02 : mise à jour bloquée, champ `l10n_ga_entry_exit_hours` « absent » de `res.company`

Date : 25/09/2026 — module `l10n_ga_hr_payroll` — statut : **en attente du « go » d'Alex** (et des réponses Q1 à Q3).

Périmètre strict : ce champ, la vue de la société, la procédure de mise à jour. Aucun calcul de paie touché.

> Cette session tourne dans un conteneur cloud (clone GitHub du dépôt), **pas sur le VPS** : pas d'accès à
> `systemctl`, `journalctl`, `ps` du service `odoo19`, ni à la base `labpaiega`, ni à Odoo Enterprise.
> Le diagnostic ci-dessous est prouvé côté dépôt et côté code Odoo 19 (sources `odoo/odoo` branche 19.0
> sur GitHub, notées `C/…`) ; la preuve « horloge » de la cause A est à relever sur le VPS (Q1, commandes
> prêtes à copier, lecture seule).

## 1. Diagnostic

### Cause B — champ absent ou mal nommé : **écartée**

| Vérification | Résultat |
|---|---|
| `grep -rn "l10n_ga_entry_exit" l10n_ga_hr_payroll/` | défini une seule fois en Python : `models/res_company.py:35` (`l10n_ga_entry_exit_hours = fields.Selection(...)`, `_inherit = 'res.company'`, `default='deduct'`, `required=True`, `help=` décrivant (a) et (b)) ; utilisé dans `views/res_company_views.xml:22`, `models/hr_payslip.py:209`, `tests/test_basic_hours.py:114,117` |
| Orthographe vue / Python | identique (`l10n_ga_entry_exit_hours`) |
| Bon modèle | `res.company` (pas `hr.version` ni `res.config.settings`) ; aucune définition ailleurs |

### Cause C — fichier Python non chargé : **écartée**

| Vérification | Résultat |
|---|---|
| `__init__.py` racine | `from . import models, wizard` |
| `models/__init__.py` | importe `res_company` |
| Syntaxe | `python3 -c "import ast; ast.parse(open('l10n_ga_hr_payroll/models/res_company.py').read())"` → `ast ok` |
| Dépendance de la vue | vue et champ dans le **même** module ; la vue parente `base.view_company_form` vient de `base` (toujours chargé) |
| Preuve par les tests | FIX 01 : `make test MODULE=l10n_ga_hr_payroll` vert sur base neuve (188 tests, `docs/completude/l10n_ga_hr_payroll_fix_01.md`), dont `test_basic_hours.py:114-117` qui lit et écrit ce champ ; l'installation valide la vue (voir §2) — une cause B ou C aurait fait échouer l'installation |

### Cause A — service non redémarré après modification du Python : **confirmée par le mécanisme, horloge à relever**

Chronologie : FIX 01 ajoute le champ (`models/res_company.py` +11 lignes) **et** la ligne de vue
(`views/res_company_views.xml` +1) — commit `3829783` du 25/09/2026 16:10:42 UTC ; les fichiers étaient
sur le disque du VPS pendant le développement, avant le commit. Erreur constatée à 15:48 GMT via le
bouton « Mettre à jour » de l'écran Applications, c'est-à-dire **dans le processus du service déjà en cours**.

Mécanisme dans Odoo 19 (sources `odoo/odoo` 19.0) :

1. Le bouton appelle `button_immediate_upgrade` → `_button_immediate_function` → `Registry.new(db, update_module=True)`
   **dans le même processus** (`C/odoo/addons/base/models/ir_module.py:696-701`, `:638`).
2. Le chargement du module appelle `load_openerp_module` (`C/odoo/modules/loading.py:178`), qui **ne réimporte pas**
   un module Python déjà présent : `if qualname in sys.modules: return` (`C/odoo/modules/module.py:501-503`).
   La classe `ResCompany` reste donc celle chargée au démarrage du service, sans le nouveau champ.
3. Les fichiers XML, eux, sont relus sur le disque ; la vue héritée est validée à son chargement
   (`_check_xml`, `C/odoo/addons/base/models/ir_ui_view.py:427`) et tout `<field>` inconnu du modèle lève
   « Field "%(field_name)s" does not exist in model "%(model_name)s" » (`…/ir_ui_view.py:1965-1969`),
   message traduit en français dans le constat.
4. L'échec annule la transaction et remet le module à l'état `installed` (`reset_modules_state`,
   `C/odoo/orm/registry.py:198-199`, `C/odoo/modules/loading.py:611-631`) : **la base n'est pas abîmée**,
   la colonne n'a pas été créée, le module reste dans sa version précédente.

Une cause B ou C aurait aussi fait échouer `make test` (processus neuf) ; or il était vert → seule A reste.

**Q1 — preuve horloge (à lancer sur le VPS, lecture seule)** :

```bash
systemctl show odoo19 -p ActiveEnterTimestamp            # démarrage du service
ps -o lstart= -p "$(systemctl show odoo19 -p MainPID --value)"
stat -c '%y %n' ~/odoo/extra-addon/l10n_ga_hr_payroll/models/res_company.py \
               ~/odoo/extra-addon/l10n_ga_hr_payroll/views/res_company_views.xml
git -C ~/odoo/extra-addon log -1 --format=%ci -- l10n_ga_hr_payroll/models/res_company.py
journalctl -u odoo19 --since "2026-09-25 15:40" --until "2026-09-25 15:55" | grep -E "ERROR|ParseError|l10n_ga_hr_payroll" | head
```

Attendu : démarrage du service **antérieur** au `stat` de `res_company.py` → A confirmée. Le relevé sera copié
dans le rapport d'incident et le rapport de complétude.

## 2. Correction (cause A) — aucun changement de code du module

Ordre recommandé (ce que fait déjà `make demo`, `tools/odoo_demo.sh`) :

1. `-u l10n_ga_hr_payroll --stop-after-init` dans un **processus neuf** (qui importe le Python du disque),
2. puis `make restart` pour que le service charge à son tour le nouveau Python.

Pourquoi pas « redémarrer d'abord » (ordre du prompt) : Odoo ne crée les colonnes qu'en mise à jour
(`registry.init_models` seulement si `update_operation`, `C/odoo/modules/loading.py:189-194`). Un service
redémarré avant la mise à jour connaît le champ mais la colonne `res_company.l10n_ga_entry_exit_hours`
n'existe pas encore : toute lecture de la société (chaque requête) échouerait (`column … does not exist`)
jusqu'au `-u`. Dans l'ordre recommandé, la seule fenêtre à risque est de quelques secondes (le service
encore ancien recharge son registre et ne sait pas afficher l'onglet Gabon de la société) et se referme au
redémarrage. **Q3 : valider cet ordre** (sinon : `stop` → `-u` → `start`, coupure de quelques dizaines de secondes).

Ensuite : Paramètres → Sociétés → onglet « Gabon — Paie et fiscalité » : le champ « Entrée / sortie en cours
de mois » est affiché, valeur (a) par défaut.

**Q2 — base concernée.** `CLAUDE.md` §5 et D-09 n'autorisent qu'une base réelle, `odoo19`, via `make demo`.
L'incident est sur l'instance `labpaiega.labtools.tech` (base `labpaiega` ?). Proposition **D-105** :
`make demo MODULE=… DB=…` avec liste blanche `odoo19 labpaiega` (défaut `odoo19`), même procédure, jamais de tests
ni de données de test dedans. Sans ton accord, la mise à jour ne vise que `odoo19` et tu lances la commande
sur `labpaiega` toi-même.

La mise à jour elle-même se fait sur le VPS (cette session n'y a pas accès) : par toi, ou par une session
Claude Code lancée sur le VPS, avec la commande ci-dessus.

## 3. Garde-fous

| # | Garde-fou | Fichier | Détail |
|---|---|---|---|
| G1 | Mise à jour d'une base réelle = processus neuf puis redémarrage, jamais le bouton | `tools/odoo_demo.sh`, `Makefile` | `DB` paramétrable avec liste blanche (si D-105) ; message final rappelant de ne pas utiliser le bouton ; `make upgrade` reste la répétition sur base neuve `test_ga_*` (déjà un processus neuf : `tools/odoo_test.sh`) — commentaire explicite dans le `Makefile` |
| G2 | Détection d'un service « en retard » sur le code | `tools/odoo_stale.sh`, cible `make stale MODULE=…` | compare le démarrage du service `odoo19` au `.py` le plus récent du module ; affiche « redémarrage nécessaire » (code 1) ; appelé en tête de `odoo_demo.sh` pour information |
| G3 | Règle dans `CLAUDE.md` §5 | `CLAUDE.md` | « Après toute modification d'un fichier `.py`, redémarrer le service Odoo avant de mettre à jour le module ; ne pas utiliser le bouton Mettre à jour de l'interface pour du code modifié » + « mise à jour d'une base réelle : `make demo` uniquement (processus neuf `-u`, puis redémarrage) » |
| G4 | Test Odoo de la vue société | `l10n_ga_hr_payroll/tests/test_res_company_view.py` | vue `res_company_view_form_l10n_ga_payroll` valide (`_check_xml`), arch combinée de `res.company` contenant `l10n_ga_entry_exit_hours` et les autres champs de l'onglet ; valeur par défaut `deduct` sur une société neuve. `make test` **ne pouvait pas** attraper la cause A (processus neuf = Python à jour) ; il attrape B et C — expliqué dans le rapport |
| G5 | C3 automatique « chaque `field name` des vues existe sur le modèle » | `tools/check_view_fields.py` + `tools/tests/test_check_view_fields.py`, hook `pre-commit` (donc `make lint`) | analyse statique (sans Odoo) : pour chaque `ir.ui.view` des modules `l10n_ga_*`, chaque `<field name="l10n_ga_…">` doit être défini en Python sur le modèle ciblé (`_name` / `_inherit`) dans le module ou ses dépendances du dépôt ; sous-vues d'un One2many/Many2many résolues via le comodèle quand le champ parent est défini dans le dépôt. Limite : les champs **standard** d'Odoo (hors préfixe `l10n_ga_`) ne sont pas vérifiables sans Odoo — c'est la validation des vues à l'installation (`make test`) qui les couvre |

## 4. Fichiers

| Fichier | Action |
|---|---|
| `docs/incidents/2026-09-25_champ_absent_res_company.md` | nouveau (explication pour Alex, 10-20 lignes) |
| `tools/check_view_fields.py`, `tools/tests/test_check_view_fields.py` | nouveaux (G5, TDD : tests d'abord) |
| `tools/odoo_stale.sh` | nouveau (G2) |
| `tools/odoo_demo.sh`, `Makefile`, `.pre-commit-config.yaml` | modifiés (G1, G2, G5) |
| `CLAUDE.md` §5, `docs/environnement_vps.md` | modifiés (G3) |
| `l10n_ga_hr_payroll/tests/test_res_company_view.py`, `tests/__init__.py` | nouveau test (G4) |
| `docs/decisions/ouvertes.md` | D-105 (bases autorisées) |
| `docs/completude/l10n_ga_hr_payroll_fix_02.md`, `docs/PROGRESS.md` | rapport et avancement |

`models/res_company.py` et `views/res_company_views.xml` : **inchangés** (le champ reste dans la vue).
Version du manifeste inchangée (`19.0.1.6.4`, déjà relevée par FIX 01) sauf si le test G4 l'impose.

## 5. Vérification et limites de cette session

- Ici : `ruff`, `tools/check_view_fields.py` sur tout le dépôt, `pytest tools/tests` ; revue du test G4.
- Sur le VPS (toi ou une session VPS) : Q1, puis `make lint`, `make test MODULE=l10n_ga_hr_payroll`,
  `make upgrade MODULE=l10n_ga_hr_payroll`, `make demo MODULE=l10n_ga_hr_payroll [DB=labpaiega]`, contrôle
  visuel de l'onglet. Tant que ces sorties ne sont pas rapportées, C4 et la vérification §6.4 du prompt sont
  classées **Bloquant** dans le rapport de complétude (pas de « vert » annoncé sans exécution).

## 6. Commits prévus

1. `docs(l10n_ga_hr_payroll): plan du FIX 02` (ce fichier)
2. `test(l10n_ga_hr_payroll): vue société Gabon valide avec l'option entrée / sortie`
3. `fix(l10n_ga_hr_payroll): procédure de mise à jour après modification du Python (incident 25/09)`
4. `chore(repo): garde-fou redémarrage avant mise à jour` (Makefile, scripts, hook, CLAUDE.md)
5. `chore(l10n_ga_hr_payroll): complétude FIX 02`
