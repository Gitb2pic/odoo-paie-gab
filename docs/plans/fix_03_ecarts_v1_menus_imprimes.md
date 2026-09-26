# FIX 03 — écarts V1, menus Comptabilité, vue et imprimés au format V1

Go d'Alex le 26/09/2026 : « go avec tes recommandations » (D-105 à D-110) + « les ID de compta vont dans la
compta, menu Analyse, on ne doit voir qu'eux » + « reprends la vue de l'ID10, son report et les reports des
autres ID dans l'addon DGI ». Analyse : `docs/analyses/ecarts_v1_hr_payroll_gb.md`.

## A. Paie (`l10n_ga_hr_payroll`) — D-106, D-107

| Élément | Fichier | Test |
|---|---|---|
| Option société `l10n_ga_default_agreement_id` (convention par défaut, `check_company`) | `models/res_company.py`, `views/res_company_views.xml` | `test_agreement` |
| Convention effective = version, sinon société : `hr.version._l10n_ga_agreement()` ; utilisée par ancienneté, heures sup., anomalies natives | `models/hr_version.py`, `models/hr_payslip.py` | `test_agreement` |
| Paramètre daté `l10n_ga_seniority_check_years` (YAML `anciennete.annees_controle_sans_convention: 2`, base 05 §4) | YAML, `param_codes.py`, XML généré | `test_param_codes`, `--check` |
| Contrôle bloquant `GA_NO_AGREEMENT` : ancienneté ≥ seuil et aucune convention effective | `models/l10n_ga_payroll_check.py` | `test_checks` |
| Contrôle bloquant `GA_OVERTIME_NO_RATE` : heures sup. sans tranche couvrante | idem | `test_checks` |

D-105 (CNSS 5 % / 18 %), D-108 (FNH 3 % au 17/07/2026), D-109 (seuil IRPP 0) : **aucun changement de code**.
D-110 : V1 lue sur place (`~/supergel-compta`), hors `addons_path`.

## B. Menus (`l10n_ga_dgi_edi`, `l10n_ga_dgi_edi_account`)

- Champ `scope` sur `l10n_ga.declaration.type` (`payroll` / `account`, défaut `payroll`), `related` stocké sur la
  déclaration. Les types ID18, ID27, ID23, ID24, ID26 passent à `account` (données du module compta).
- Paie > Déclarations Gabon : actions filtrées `scope = payroll` (Échéances, Déclarations, ID10, DTS, DAS, ID28).
- Comptabilité > **Analyse** > « Déclarations DGI » : Échéances, Déclarations, Quittances filtrées `scope = account`.
- Sécurité : accès `account.group_account_user` (lecture / calcul) aux déclarations ; règle de groupe
  « comptable : imprimés de la comptabilité seulement » + règle « paie : tout » (les règles de groupe s'additionnent).

## C. Vue et imprimé ID10 au format V1 (ADR-20)

- Vue formulaire dédiée ID10 (cadres 1 à 4 de la V1) : champs d'affichage non stockés **lus sur les cases
  figées** (`line_ids`), jamais recalculés — la règle d'or 8 porte sur la valeur, qui reste stockée.
- Imprimé QWeb au format V1 (`report_id10_v1`), lu sur les cases ; devient `report_id` du type ID10 (le PDF de
  l'instantané suit). Le rendu « classeur » reste disponible en second rapport.

## D. Autres imprimés au format V1

DTS, DAS (ID20, ID21, ID22, ID19 par salarié), ID28, ID18, ID27, ID23, ID24, ID26 : même principe (QWeb lu sur
cases et détails figés, briques communes `dgi_formulaire_*` réécrites), `report_id` du type remplacé,
rendu « classeur » conservé.

## Risques

- Tests existants qui lisent le PDF (texte du classeur) : à adapter au nouveau rendu.
- Anomalie bloquante nouvelle en démo (`odoo19`) : 85 salariés sans convention → renseigner la convention
  par défaut de la société (EXEMPLE tronc commun ou vraie convention) avant la prochaine paie.
