# 04 — Design patterns retenus

Chaque patron répond à un problème concret de l'addon. Les extraits de code sont des squelettes Odoo 19 (syntaxe vérifiée sur Community 19.0 : `models.Constraint`, `fields.Json`, `_read_group`, `@api.model_create_multi`) ; les appels à `hr_payroll` 🔒 sont à confirmer sur le code Enterprise.

| # | Patron | Problème réglé | Où |
|---|---|---|---|
| 1 | Functional Core / Imperative Shell (hexagonal) | Calcul fiscal testable sans base | `ga_fiscal_core` |
| 2 | Adapter (couche anti-corruption) | Isoler le noyau des objets `hr.payslip` Enterprise | `PayslipFactsAdapter` |
| 3 | Parameter Object + Temporal Property | Taux qui changent en cours d'année | `FiscalParams` chargés depuis `hr.rule.parameter` |
| 4 | Strategy | Un algorithme de collecte par imprimé | générateurs ID10, ID28, DAS, DTS, CA01… |
| 5 | Registry / Factory | Trouver la stratégie d'un type sans `if/elif` | `l10n_ga.declaration.generator` |
| 6 | Template Method | Même cycle pour toutes les déclarations | `l10n_ga.declaration.action_compute` |
| 7 | State | Cycle de vie brouillon → payée, transitions gardées | `state` + méthodes `action_*` |
| 8 | Chain of Responsibility | Contrôles de cohérence composables, avant paie et avant dépôt | `CheckRule` chaînés |
| 9 | Builder | Rendu Excel cellule par cellule depuis les cases | `XlsxDeclarationBuilder` |
| 10 | Memento / Snapshot | Déclaration figée après validation | lignes + détails + pièces jointes, `frozen=True` |
| 11 | Observer (hooks ORM) | Déclencher sans intervention humaine | surcharge de la validation du lot, `ir.cron` |
| 12 | Specification | Règles d'octroi des prêts combinables et dérogeables | `l10n_ga.employee.loan._check_eligibility` |
| 13 | Pipes and Filters | Import Excel des variables : lire, valider, prévisualiser, écrire | assistant `l10n_ga.payslip.input.import` |
| 14 | Data Mapper | Reprise depuis `hr_payroll_gb` sans dépendre de ses modèles | `l10n_ga_hr_payroll_migration`, table `l10n_ga.migration.map` |
| 15 | Report de reliquat (état porté par l'enregistrement) | Arrondi des paies en espèces sans perte d'argent | champ `l10n_ga_rounding_carry` sur le bulletin |

## 1. Functional Core / Imperative Shell

Problème : les règles salariales Odoo sont du code Python stocké en base (`amount_python_compute`) ; y mettre le barème IRPP rend le calcul intestable et dupliqué. Solution : tout le calcul vit dans un package Python pur, sans import `odoo`, appelé par une seule méthode du bulletin.

```python
# l10n_ga_hr_payroll/lib/ga_fiscal_core/engine.py  — aucun import odoo
from dataclasses import dataclass

@dataclass(frozen=True)
class PayslipFacts:
    gains_total: float
    social_excluded: float
    tax_exempt: float
    marital: str
    children: int
    disabled_children: int = 0
    extra_half_part: bool = False
    forced_parts: float | None = None
    presence_ratio: float = 1.0
    ytd_bonus_exempted: float = 0.0
    month: int = 1
    is_last_payslip_of_year: bool = False
    ytd_taxable_base: float = 0.0
    ytd_irpp_withheld: float = 0.0

@dataclass(frozen=True)
class PayResult:
    social_base: float
    cnss_employee: float
    cnamgs_employee: float
    tcs_base: float
    tcs: float
    tax_parts: float
    irpp: float
    irpp_regularisation: float
    cnss_employer_pf: float
    cnss_employer_at: float
    cnss_employer_avid: float
    cnamgs_employer: float
    fnh: float
    cfp: float

def compute(facts: PayslipFacts, p: "FiscalParams") -> PayResult:
    ...  # algorithme du fichier 04 §7 de la base de connaissance
```

Tests : `pytest` directement sur `engine.compute` avec les 4 exemples validés (fichier 04 §8), exécutés en quelques millisecondes et dans la CI sans lancer Odoo.

## 2. Adapter (anti-corruption)

Problème : la structure d'`hr.payslip` Enterprise (catégories, `version_id` ou `contract_id`, entrées, prestations) peut changer entre versions. Solution : un seul adaptateur traduit le bulletin en `PayslipFacts` ; si Odoo change, seul l'adaptateur change.

```python
# l10n_ga_hr_payroll/models/hr_payslip.py
from odoo import models
from ..lib.ga_fiscal_core import engine

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _l10n_ga_facts(self, categories):
        self.ensure_one()
        version = self.version_id  # ✔ sprint 0 point 1 (hr_payslip.py:114)
        return engine.PayslipFacts(
            gains_total=categories['GROSS'],
            social_excluded=categories.get('GA_SOC_EXCL', 0.0),
            tax_exempt=categories.get('GA_TAX_EXEMPT', 0.0),
            marital=version.marital,
            children=version.children,
            disabled_children=version.l10n_ga_disabled_children,
            extra_half_part=version.l10n_ga_extra_half_part,
            forced_parts=version.l10n_ga_tax_parts_forced or None,
            ytd_bonus_exempted=self._l10n_ga_ytd('GA_BONUS_EXEMPT'),
            month=self.date_to.month,
        )
```

## 3. Parameter Object + propriété temporelle

Problème : réforme CNSS au 01/01/2026, FNH 3 % au 17/07/2026, précompte loyers changé deux fois. Solution : `hr.rule.parameter` (valeurs datées, standard `hr_payroll` 🔒) chargé en un objet immuable pour la date de fin du bulletin.

```python
@dataclass(frozen=True)
class FiscalParams:
    cnss_employee_rate: float
    cnss_ceiling: float
    cnamgs_employee_rate: float
    cnamgs_ceiling: float
    tcs_rate: float
    tcs_monthly_exemption: float
    tcs_deduct_cnamgs: bool
    fp_rate: float
    fp_annual_cap: float
    irpp_brackets: tuple  # ((de, a, taux, constante), ...)
    fnh_rate: float
    cfp_rate: float
    smig: float
    # ...

# côté Odoo
def _l10n_ga_params(self):
    get = lambda code: self._rule_parameter(code)  # ✔ sprint 0 point 11, date = date_to du bulletin (D-06)
    return engine.FiscalParams(
        cnss_employee_rate=get('l10n_ga_cnss_employee_rate'),
        irpp_brackets=tuple(get('l10n_ga_irpp_brackets')),
        ...
    )
```

Les valeurs initiales sont générées à partir de `parametres_fiscaux_gabon_2026.yaml` vers `data/hr_rule_parameters_data.xml` par un script de build ; toute modification de taux = nouvelle valeur datée, jamais une réécriture.

## 4. Strategy + 5. Registry / Factory

Problème : chaque imprimé collecte des données différentes (bulletins, écritures, taxes). Solution : une stratégie par imprimé, enregistrée sous une clé ; le type de déclaration (donnée XML) porte la clé.

```python
# l10n_ga_dgi_edi/models/declaration_generator.py
from odoo import models

class DeclarationGenerator(models.AbstractModel):
    _name = 'l10n_ga.declaration.generator'
    _description = "Registre des générateurs d'imprimés"

    def _get(self, key):
        model = f'l10n_ga.declaration.generator.{key.lower()}'
        if model not in self.env:
            raise KeyError(key)
        return self.env[model]

class GeneratorBase(models.AbstractModel):
    _name = 'l10n_ga.declaration.generator.base'
    _description = "Stratégie de collecte (interface)"

    def _collect(self, declaration):  raise NotImplementedError
    def _fill(self, declaration, facts):  raise NotImplementedError   # -> {box_code: value}
    def _details(self, declaration, facts):  return []
    def _checks(self, declaration, facts):  return []

class GeneratorID10(models.AbstractModel):
    _name = 'l10n_ga.declaration.generator.id10'
    _inherit = 'l10n_ga.declaration.generator.base'
    _description = "ID10 — retenues sur salaires et CFP"

    def _collect(self, declaration):
        lines = self.env['hr.payslip.line']._read_group(
            [('slip_id.company_id', '=', declaration.company_id.id),
             ('slip_id.state', 'in', ('validated', 'paid')),     # ✔ ADR-19 : plus d'état 'done' en 19
             ('slip_id.l10n_ga_payment_date', '>=', declaration.date_from),
             ('slip_id.l10n_ga_payment_date', '<=', declaration.date_to),
             ('code', 'in', ('IRPP', 'TCS', 'FNH', 'CFP_BASE', 'CFP'))],
            ['code'], ['total:sum'])
        return {code: total for code, total in lines}

    def _fill(self, declaration, facts):
        return {'L40': facts.get('IRPP', 0), 'L41': facts.get('TCS', 0),
                'L42': facts.get('FNH', 0), 'L43': sum(facts.get(c, 0) for c in ('IRPP', 'TCS', 'FNH')),
                'R54': facts.get('CFP_BASE', 0), 'R55': 0.005, 'R56': facts.get('CFP', 0)}
```

Ajouter un imprimé = un fichier de données (type + cases) + un modèle abstrait de générateur, sans modifier le moteur (principe ouvert/fermé). Le module V2 `l10n_ga_dgi_edi_account` ajoute ses générateurs de la même façon.

## 6. Template Method

Problème : toutes les déclarations suivent le même cycle (collecter, remplir, détailler, contrôler, rendre). Solution : l'algorithme est fixé dans `l10n_ga.declaration` ; seules les étapes variables sont déléguées à la stratégie.

```python
class L10nGaDeclaration(models.Model):
    _name = 'l10n_ga.declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Déclaration fiscale ou sociale Gabon"

    def action_compute(self):
        for decl in self:
            decl._ensure_state('draft', 'computed')
            gen = self.env['l10n_ga.declaration.generator']._get(decl.type_id.generator_key)
            facts = gen._collect(decl)                     # étape variable
            decl._write_boxes(gen._fill(decl, facts))      # étape fixe
            decl._write_details(gen._details(decl, facts)) # étape fixe
            decl._run_checks(gen._checks(decl, facts))     # étape fixe + règles communes
            decl.state = 'computed'
```

## 7. State

Problème : une déclaration déposée ne doit plus bouger ; certaines transitions exigent un droit. Solution : champ `state` avec transitions explicites et gardes.

```python
    state = fields.Selection([
        ('draft', 'Brouillon'), ('computed', 'Calculée'), ('validated', 'Validée'),
        ('filed', 'Déposée'), ('paid', 'Payée'), ('cancel', 'Annulée')],
        default='draft', required=True, tracking=True)

    _TRANSITIONS = {
        'draft': {'computed', 'cancel'},
        'computed': {'computed', 'draft', 'validated'},
        'validated': {'computed', 'filed'},
        'filed': {'paid'},
        'paid': set(),
    }

    def _ensure_state(self, *allowed):
        bad = self.filtered(lambda d: d.state not in allowed)
        if bad:
            raise UserError(_("Action impossible dans l'état %s.", bad[0].state))
```

## 8. Chain of Responsibility (règles de contrôle, deux périmètres)

Problème : les contrôles (salarié sans n° CNSS, total ID21 ≠ total ID10, bulletin sous le SMIG…) sont nombreux et partagés entre imprimés. Solution : chaque contrôle est un objet indépendant qui renvoie ses anomalies ; la déclaration enchaîne les contrôles communs puis ceux du générateur.

```python
class CheckRule:
    code = None
    severity = 'blocking'
    def applies(self, decl): return True
    def run(self, decl, facts): return []   # -> [(severity, code, message, record)]

class MissingCnssNumber(CheckRule):
    code = 'GA_NO_CNSS'
    def run(self, decl, facts):
        emps = decl.detail_ids.employee_id.filtered(lambda e: not e.ssnid)
        return [(self.severity, self.code, _("%s : n° CNSS manquant", e.name), e) for e in emps]

COMMON_CHECKS = [MissingCnssNumber(), DuplicatePeriod(), ParameterMissing(), TotalsMatchDetails()]
PAYROLL_CHECKS = [MissingCnssNumber(), MissingHireDate(), WageBelowGradeMinimum(), MissingBankAccount(),
                  ForcedPartsWithoutReason(), LoanInstallmentOver40Pct(), NoVersionOnPeriod()]
```

Après le benchmark, la même chaîne sert aussi **avant la paie** (F8) : `PAYROLL_CHECKS` s'exécute sur le lot avant calcul, et toutes les anomalies vont dans un modèle unique `l10n_ga.check.issue` (périmètre lot ou déclaration), affiché sur le lot et dans l'écran « Contrôle DAS » repris de la V1.

## 9. Builder (rendu Excel)

Problème : les imprimés DGI ont une mise en page imposée ; les modèles Excel fournis contiennent des formules fausses. Solution : un constructeur écrit des valeurs (jamais de formules) dans une copie du gabarit, case par case, à partir de `box.cell_ref`.

```python
class XlsxDeclarationBuilder:
    def __init__(self, template_bytes): ...
    def header(self, company, period): ...        # NIF, raison sociale, exercice, mois
    def boxes(self, lines): ...                   # line.box_id.cell_ref -> valeur
    def table(self, sheet, start_row, rows): ...  # ID21 paginé (39 lignes / feuille)
    def build(self) -> bytes: ...
```

Le rendu PDF suit le même principe avec un gabarit QWeb par imprimé (`report_l10n_ga_id10`, `report_l10n_ga_das_id19`…).

Après le benchmark, le constructeur a deux moteurs derrière la même interface (F10) : `XlsmTemplateRenderer` remplit les classeurs officiels DGI de la V1 (`edi-annexe-ID19/21/23/26.xlsm`) avec `openpyxl.load_workbook(..., keep_vba=True)` — `xlsxwriter` ne sait pas ouvrir un fichier existant — et `XlsxRenderer` (`xlsxwriter`) produit les états neufs (livre de paie, virements, billetage). `openpyxl` et `xlsxwriter` sont tous deux des dépendances d'Odoo 19 ✔ (`requirements.txt`).

## 10. Memento / Snapshot

Problème : un bulletin recalculé après dépôt ne doit pas modifier la déclaration déposée (preuve en cas de contrôle). Solution : à la validation, les valeurs de cases et les détails sont stockés (pas de champs calculés), les fichiers générés sont joints, un empreinte (hash SHA-256 des lignes) est enregistrée ; toute correction crée une déclaration rectificative liée (`rectified_id`).

## 11. Observer (événements ORM et cron)

Problème : exigence « génération automatique sans intervention humaine ». Solution : se brancher sur les événements du cycle de paie et sur un cron quotidien.

```python
class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):        # ✔ ADR-19 : appelé par le lot ET par un bulletin seul
        res = super().action_payslip_done()
        self.env['l10n_ga.declaration']._l10n_ga_on_payslips_done(self)
        return res
```

```xml
<record id="ir_cron_l10n_ga_declaration_schedule" model="ir.cron">
  <field name="name">Gabon : préparer les déclarations à échéance</field>
  <field name="model_id" ref="model_l10n_ga_declaration"/>
  <field name="code">model._cron_prepare_due_declarations()</field>
  <field name="interval_number">1</field>
  <field name="interval_type">days</field>
</record>
```

Le cron crée les déclarations brouillon J-10 avant l'échéance, les calcule, et planifie une activité (`mail.activity`) pour le déclarant ; une anomalie bloquante génère une activité « à corriger ».

## 12. Specification (octroi des prêts)

Problème : les conditions d'octroi (ancienneté ≥ 2 ans, mensualité ≤ 40 % du net, encours ≤ plafond) viennent du freelance, varient selon les sociétés et peuvent être levées par une dérogation RH. Solution : chaque condition est une spécification indépendante, paramétrée, que l'on combine.

```python
class Spec:
    def ok(self, loan): raise NotImplementedError
    def reason(self, loan): return ''
    def __and__(self, other): return AndSpec(self, other)

class MinSeniority(Spec):
    def __init__(self, years): self.years = years
    def ok(self, loan): return loan.employee_id._l10n_ga_seniority_years(loan.date) >= self.years
    def reason(self, loan): return _("Ancienneté inférieure à %s ans", self.years)

def _check_eligibility(self):
    p = self._l10n_ga_loan_params()           # paramètres datés + plafond société
    spec = MinSeniority(p.min_years) & MaxInstallmentRatio(p.max_ratio) & MaxOutstanding(p.ceiling)
    failures = [s.reason(self) for s in spec.leaves() if not s.ok(self)]
    if failures and not self.hr_override:
        raise UserError("\n".join(failures))
```

## 13. Pipes and Filters (import des variables)

Problème : l'import Excel doit refuser proprement les lignes fausses sans bloquer tout le lot, et rester testable. Solution : une suite d'étapes indépendantes, chacune prend une liste de lignes et renvoie les lignes valides plus ses anomalies.

```python
PIPELINE = [read_workbook, normalise_headers, resolve_employee, resolve_input_type,
            parse_amount, check_in_batch, dedupe]
def run(rows):
    issues = []
    for step in PIPELINE:
        rows, step_issues = step(rows)
        issues += step_issues
    return rows, issues            # aperçu, puis écriture dans hr.payslip.input / hr.work.entry
```

## 14. Data Mapper (reprise depuis `hr_payroll_gb`)

Problème : reprendre les données du freelance sans que la V2 dépende de ses modèles (qui ont des défauts et seront désinstallés). Solution : le module de reprise lit les tables `hr_payroll_gb` par SQL et convertit chaque enregistrement par une table de correspondance explicite (`l10n_ga.migration.map` : source, code source, cible, code cible, règle de conversion). Les codes non mappés produisent une anomalie de reprise au lieu d'être ignorés. Aucun import Python de `hr_payroll_gb`.

## 15. Report de reliquat (arrondi espèces)

Problème : payer en espèces un net arrondi à 500 FCFA sans voler ni surpayer le salarié, et sans dupliquer la règle `NET` (défaut B1 du freelance). Solution : `NET` reste unique ; la règle `GA_ROUND` calcule `montant = floor((NET + reliquat précédent) / 500) × 500` et stocke `reliquat = NET + reliquat précédent − montant` sur le bulletin ; le bulletin suivant du salarié lit ce champ (`GA_ROUND_PREV`). Au solde de tout compte, le reliquat est versé intégralement.

## Anti-patrons écartés

| Écarté | Raison |
|---|---|
| Barème IRPP codé dans `amount_python_compute` | Non testable, dupliqué, faux dès le prochain changement de loi |
| Déclarations calculées en champs `compute` non stockés | Une déclaration déposée changerait avec les bulletins |
| Remplir les modèles Excel DGI existants avec leurs formules | 9 anomalies de formules relevées dans la DAS v3 |
| Surcharger `hr.employee` pour les données fiscales | En Odoo 19 elles doivent vivre sur `hr.version` pour être datées |
| Deux règles de même code selon le mode de paiement (freelance, B1) | La seconde écrase la première : pas de net pour les espèces ou les chèques |
| Redéfinir `wage` ou `number` (freelance, M8 et M9) | Casse les fonctions standard d'Odoo ; le minimum conventionnel devient un contrôle |
| Variables du mois stockées sur la fiche salarié (freelance) | Hors du cycle standard `hr.payslip.input` et non historisées |
| Bulletin PDF lisant la fiche du jour (freelance) | Un ancien bulletin réimprimé change ; le bulletin figé lit ses propres valeurs |
