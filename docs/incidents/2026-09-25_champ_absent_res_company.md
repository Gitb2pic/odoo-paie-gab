# Incident du 25/09/2026 — « Le champ l10n_ga_entry_exit_hours n'existe pas dans le modèle res.company »

**Ce qui s'est passé.** À 15:48, la mise à jour de `l10n_ga_hr_payroll` lancée depuis le bouton « Mettre à jour » de l'écran Applications a échoué. Le service Odoo qui l'a exécutée (processus 436583) tournait depuis **15:32**. Or le FIX 01 a ajouté le champ `l10n_ga_entry_exit_hours` dans `models/res_company.py` à **15:44**, avec la vue qui l'affiche. Le service avait donc en mémoire l'ancien code Python, sans ce champ, alors qu'il a lu la nouvelle vue sur le disque. Preuves : heure de démarrage du processus dans `journalctl -u odoo19`, date du fichier (`stat`), et le même processus 436583 dans le message d'erreur. Le code n'était pas en cause : sur une base neuve, avec un processus neuf, les 188 tests de la paie passent et la vue s'installe.

**Pourquoi Odoo refuse.** Au chargement d'un fichier XML de vue, Odoo vérifie immédiatement que chaque champ cité existe dans le modèle tel qu'il le connaît en mémoire. Un champ inconnu est une erreur bloquante : toute la mise à jour du module est annulée.

**Redémarrer ou mettre à jour ?**
- *Redémarrer le service* : relance le programme et relit tout le **code Python** (modèles, champs, méthodes).
- *Mettre à jour le module* : relit les **données** (vues XML, droits, paramètres) et adapte le **schéma** de la base (nouvelles colonnes). Si le processus qui le fait a été lancé avant la modification du Python, il ne connaît pas les nouveaux champs.

**Ce qui a été fait.** Le service a été redémarré à 16:14:58. Depuis, le module est en 19.0.1.6.4 et la colonne existe. Aucun changement de code n'a été nécessaire, et le champ est resté dans la vue.

**Pour que ça ne revienne pas.**
1. Pour du code modifié, on met toujours à jour par `make demo MODULE=…` (alias `make update-demo`) : un processus neuf fait la mise à jour, puis le service redémarre. Jamais par le bouton de l'interface.
2. La règle est écrite dans `CLAUDE.md` §5.
3. `make lint` vérifie désormais que chaque champ `l10n_ga_…` cité dans une vue existe bien en Python sur le bon modèle (`tools/check_view_fields.py`).
