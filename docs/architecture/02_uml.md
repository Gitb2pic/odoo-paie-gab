# 02 — Modélisation UML

Conventions : les classes préfixées `hr.` ou `account.` sont des modèles Odoo existants (étendus) ; les classes `l10n_ga.*` sont nouvelles ; `ga_fiscal_core` est le noyau Python pur. 🔒 = modèle Enterprise dont la structure exacte doit être vérifiée sur le code source Enterprise 19.0.

## 1. Diagrammes de cas d'utilisation

### 1.1 Paie

```mermaid
flowchart LR
  ADM([Administrateur])
  RH([Responsable RH])
  GP([Gestionnaire paie])
  CPT([Comptable])
  subgraph S1["Système : paie Gabon"]
    UC1((Paramétrer taux<br/>et barèmes datés))
    UC2((Gérer dossier salarié<br/>parts, CNSS, NIF, grade))
    UC15((Octroyer un prêt<br/>échéancier, dérogation))
    UC3((Saisir ou importer<br/>les variables Excel))
    UC16((Contrôler avant paie<br/>anomalies salariés))
    UC4((Calculer un lot<br/>de bulletins))
    UC6((Régulariser l'IRPP<br/>annuel / départ))
    UC5((Valider et comptabiliser<br/>la paie))
    UC17((Payer : virements,<br/>espèces arrondies, billetage))
    UC18((Éditer livre de paie<br/>et état des charges))
    UC19((Reprendre les données<br/>depuis hr_payroll_gb))
  end
  ADM --> UC1
  ADM --> UC19
  GP --> UC2
  RH --> UC15
  GP --> UC3
  GP --> UC4
  GP --> UC6
  CPT --> UC5
  CPT --> UC17
  GP --> UC18
  UC4 -. include .-> UC16
  UC4 -. include .-> UC6
```

### 1.2 Déclarations

```mermaid
flowchart LR
  DF([Déclarant fiscal])
  CRON([Échéancier ir.cron])
  CPT([Comptable])
  subgraph S2["Système : déclarations DGI / CNSS / CNAMGS"]
    UC13((Créer les déclarations<br/>à échéance))
    UC7((Générer ID10 / ID28))
    UC8((Générer DTS CNSS<br/>et CNAMGS))
    UC9((Générer la DAS<br/>ID19 à ID22))
    UC20((Générer ID18 / ID27<br/>et annexes DAS ID23/24/26))
    UC14((V2 : CA01, ID30,<br/>ID01, patente, CFU))
    UC10((Contrôler la cohérence))
    UC11((Valider, figer,<br/>exporter Excel / PDF))
    UC12((Enregistrer dépôt<br/>et quittances multiples))
  end
  CRON --> UC13
  DF --> UC7
  DF --> UC8
  DF --> UC9
  CPT --> UC14
  CPT --> UC20
  UC20 -. include .-> UC10
  DF --> UC11
  DF --> UC12
  UC7 -. include .-> UC10
  UC8 -. include .-> UC10
  UC9 -. include .-> UC10
  UC14 -. include .-> UC10
  UC11 -. include .-> UC10
```

## 2. Diagramme de classes — domaine paie

```mermaid
classDiagram
  direction LR
  class HrEmployee["hr.employee"] {
    +version_id : hr.version
    +version_ids : hr.version[*]
    +_get_version(date) hr.version
  }
  class HrVersion["hr.version (étendu)"] {
    +date_version : Date
    +wage : Monetary
    +marital : Selection
    +children : Integer
    +ssnid : Char  « n° CNSS »
    +l10n_ga_cnamgs_number : Char
    +l10n_ga_nif : Char
    +l10n_ga_disabled_children : Integer
    +l10n_ga_extra_half_part : Boolean
    +l10n_ga_tax_parts : Float «calculé»
    +l10n_ga_tax_parts_forced : Float
    +l10n_ga_nationality_code : Selection «1..4»
    +l10n_ga_transport_trips : Selection «2|4»
    +l10n_ga_company_car : Boolean
    +l10n_ga_agreement_id : Many2one
    +l10n_ga_job_code / level_code : Char
    +l10n_ga_grade_id : Many2one
    +l10n_ga_payment_mode : Selection «virement|espèces|chèque»
    +_compute_l10n_ga_tax_parts()
  }
  class ResCompany["res.company (étendu)"] {
    +l10n_ga_nif : Char
    +l10n_ga_cnss_employer_number : Char
    +l10n_ga_cnamgs_employer_number : Char
    +l10n_ga_tax_center_code : Char
    +l10n_ga_taxpayer_segment : Selection «DGE|CIME|autre»
    +l10n_ga_cfp_on_id28 : Boolean
    +l10n_ga_fnh_employee_share : Float
    +l10n_ga_cash_rounding : Integer «500»
    +l10n_ga_loan_ceiling : Monetary
  }
  class Agreement["l10n_ga.collective.agreement"] {
    +name : Char
    +code : Char
    +seniority_start_years : Integer
    +seniority_rate_start : Float
    +seniority_rate_step : Float
    +seniority_rate_max : Float
  }
  class OvertimeRate["l10n_ga.overtime.rate"] {
    +agreement_id
    +work_entry_type_id
    +band_from_hour / band_to_hour : Float
    +period : Selection «jour|nuit|dimanche|férié»
    +rate : Float
  }
  class Payslip["hr.payslip 🔒 (étendu)"] {
    +employee_id / version_id
    +date_from / date_to
    +l10n_ga_payment_date : Date
    +l10n_ga_ytd_bonus_exempt : Monetary «calculé»
    +l10n_ga_tax_parts_used / bases / plafonds «figés»
    +l10n_ga_ytd_gross / taxable / irpp / tcs / cnss «figés»
    +l10n_ga_rounding_carry : Monetary
    +_l10n_ga_facts(categories) PayslipFacts
    +_l10n_ga_params() FiscalParams
    +_l10n_ga_compute(code, categories) float
  }
  class PayslipLine["hr.payslip.line 🔒"] {
    +code : Char
    +category_id
    +amount / quantity / rate / total
  }
  class SalaryRule["hr.salary.rule 🔒 (étendu)"] {
    +code : Char
    +category_id
    +amount_python_compute : Text
    +l10n_ga_social_base : Selection «soumis|exclu|plafonné»
    +l10n_ga_tax_base : Selection «imposable|exonéré|plafonné»
    +l10n_ga_exemption_cap_param : Char
    +l10n_ga_in_leave_base : Boolean
    +l10n_ga_in_severance_base : Boolean
    +l10n_ga_das_column : Selection
  }
  class RuleParameter["hr.rule.parameter 🔒"] {
    +code : Char
    +parameter_version_ids
  }
  class RuleParameterValue["hr.rule.parameter.value 🔒"] {
    +date_from : Date
    +parameter_value : Text
  }
  class Grade["l10n_ga.agreement.grade"] {
    +agreement_id
    +category / echelon : Char
    +min_wage : Monetary
    +hourly_rate : Float
    +date_from : Date
  }
  class Loan["l10n_ga.employee.loan"] {
    +employee_id / company_id
    +amount / installment : Monetary
    +installments_count : Integer
    +state : Selection «brouillon|approuvé|en cours|soldé|annulé»
    +hr_override : Boolean + motif
    +action_approve()
    +_check_eligibility() «Specification»
  }
  class LoanLine["l10n_ga.employee.loan.line"] {
    +date / amount
    +state : Selection «à payer|retenue|reportée»
    +payslip_id
  }
  class YtdOpening["l10n_ga.ytd.opening"] {
    +employee_id / year
    +gross / taxable / irpp / tcs / cnss
    +bonus_exempted : Monetary
  }
  class InputImport["l10n_ga.payslip.input.import (assistant)"] {
    +payslip_run_id
    +file : Binary
    +action_template() / action_check() / action_import()
  }
  class FiscalCore["ga_fiscal_core.engine"] {
    <<Python pur>>
    +compute(facts, params) PayResult
    +tax_parts(marital, children, disabled, extra) float
    +irpp_monthly(base, parts, params) float
    +tcs(base, params) float
    +social(base, params) dict
  }
  HrEmployee "1" --> "1..*" HrVersion : versions (_inherits)
  HrVersion "*" --> "0..1" Agreement
  Agreement "1" *-- "*" OvertimeRate
  ResCompany "1" --> "*" HrEmployee
  Payslip "*" --> "1" HrEmployee
  Payslip "*" --> "1" HrVersion
  Payslip "1" *-- "*" PayslipLine
  PayslipLine "*" --> "1" SalaryRule
  RuleParameter "1" *-- "1..*" RuleParameterValue
  Payslip ..> FiscalCore : délègue le calcul
  Agreement "1" *-- "*" Grade
  HrVersion "*" --> "0..1" Grade
  HrEmployee "1" --> "*" Loan
  Loan "1" *-- "1..*" LoanLine
  LoanLine "*" --> "0..1" Payslip : retenue par
  HrEmployee "1" --> "*" YtdOpening
  Payslip ..> YtdOpening : cumuls de l'année de bascule
  InputImport ..> Payslip : crée hr.payslip.input
  Payslip ..> RuleParameter : _rule_parameter(code, date)
```

## 3. Diagramme de classes — moteur de déclarations

```mermaid
classDiagram
  direction TB
  class DeclarationType["l10n_ga.declaration.type"] {
    +code : Char «ID10, ID28, DAS, DTS_CNSS…»
    +name : Char
    +authority : Selection «dgi|cnss|cnamgs»
    +periodicity : Selection «mensuel|trimestriel|annuel»
    +due_rule : Char «ex. M+1 J15»
    +period_basis : Selection «date_paiement|periode|annee»
    +generator_key : Char
    +xlsx_template : Binary
    +report_id : ir.actions.report
    +active_from / active_to : Date
  }
  class DeclarationBox["l10n_ga.declaration.box"] {
    +type_id
    +code : Char «L40, L41, R49…»
    +label : Char
    +sequence : Integer
    +cell_ref : Char «P40»
    +value_kind : Selection «montant|nombre|texte|date»
    +is_total : Boolean
  }
  class Declaration["l10n_ga.declaration"] {
    +name : Char
    +company_id
    +type_id
    +date_from / date_to : Date
    +due_date : Date
    +state : Selection
    +amount_total : Monetary
    +filing_date / filing_number : Char
    +payment_ids : l10n_ga.declaration.payment[*]
    +rectified_id / sha256 : Char
    +attachment_ids
    +action_compute()
    +action_validate()
    +action_mark_filed()
    +action_mark_paid()
    +action_reset_draft()
  }
  class DeclarationLine["l10n_ga.declaration.line"] {
    +declaration_id
    +box_id
    +value_amount : Monetary
    +value_text : Char
  }
  class DeclarationDetail["l10n_ga.declaration.detail"] {
    +declaration_id
    +box_id
    +employee_id / partner_id
    +payslip_line_ids / move_line_ids
    +amount : Monetary
    +payload : Json «colonnes DAS»
  }
  class CheckIssue["l10n_ga.check.issue"] {
    +scope : Selection «lot de paie|déclaration»
    +payslip_run_id / declaration_id
    +severity : Selection «bloquant|avertissement»
    +code / message : Char
    +res_model / res_id
  }
  class DeclarationPayment["l10n_ga.declaration.payment"] {
    +declaration_id
    +date / amount
    +receipt_number : Char
    +kind : Selection «RS|FNH|CFP|autre»
    +move_id : account.move
  }
  class GeneratorRegistry["l10n_ga.declaration.generator"] {
    <<AbstractModel - registre>>
    +_get(key) Generator
  }
  class Generator["l10n_ga.declaration.generator.base"] {
    <<AbstractModel - interface Strategy>>
    +_collect(decl) Facts
    +_fill(decl, facts) dict
    +_details(decl, facts) list
    +_checks(decl, facts) list
  }
  class GenID10
  class GenID28
  class GenDAS
  class GenDTS
  class GenDASFees["GenID23 / ID24 / ID26"]
  class GenRAS["GenID18 / ID27"]
  class GenCA01["GenCA01 (V2)"]
  class Renderer {
    <<interface>>
    +render(decl) bytes
  }
  class XlsxRenderer["XlsxRenderer (xlsxwriter, états neufs)"]
  class XlsmRenderer["XlsmTemplateRenderer (openpyxl keep_vba)"]
  class PdfRenderer
  DeclarationType "1" *-- "1..*" DeclarationBox
  DeclarationType "1" --> "*" Declaration
  Declaration "1" *-- "*" DeclarationLine
  Declaration "1" *-- "*" DeclarationDetail
  Declaration "1" *-- "*" CheckIssue
  Declaration "1" *-- "*" DeclarationPayment
  DeclarationLine "*" --> "1" DeclarationBox
  Declaration ..> GeneratorRegistry
  GeneratorRegistry ..> Generator
  Generator <|.. GenID10
  Generator <|.. GenID28
  Generator <|.. GenDAS
  Generator <|.. GenDTS
  Generator <|.. GenDASFees
  Generator <|.. GenRAS
  Generator <|.. GenCA01
  Renderer <|.. XlsxRenderer
  Renderer <|.. PdfRenderer
  Renderer <|.. XlsmRenderer
  Declaration ..> Renderer
```

## 4. Séquence — calcul d'un bulletin

```mermaid
sequenceDiagram
  autonumber
  actor GP as Gestionnaire paie
  participant RUN as hr.payslip.run 🔒
  participant SLIP as hr.payslip 🔒
  participant RULE as hr.salary.rule (Gabon)
  participant PARAM as hr.rule.parameter
  participant ADP as Adaptateur PayslipFacts
  participant CORE as ga_fiscal_core
  GP->>RUN: Générer / calculer le lot
  RUN->>SLIP: compute_sheet()
  loop pour chaque règle, par séquence
    SLIP->>RULE: évaluer amount_python_compute
    alt règle de gain (BASE, ANC, HS, primes)
      RULE-->>SLIP: montant (entrées, prestations, version)
    else règle fiscale (CNSS_SAL, TCS, IRPP…)
      RULE->>SLIP: _l10n_ga_compute("IRPP")
      SLIP->>ADP: construire PayslipFacts (catégories, cumuls YTD, version)
      SLIP->>PARAM: _rule_parameter(codes, date_to)
      PARAM-->>SLIP: taux, plafonds, barème en vigueur
      SLIP->>CORE: compute(facts, params)
      CORE-->>SLIP: PayResult (mis en cache sur le bulletin)
      SLIP-->>RULE: montant IRPP
    end
    RULE-->>SLIP: ligne hr.payslip.line
  end
  SLIP-->>RUN: bulletin calculé (NET, COUT)
```

## 5. Séquence — clôture mensuelle et ID10

```mermaid
sequenceDiagram
  autonumber
  actor CPT as Comptable
  actor DF as Déclarant fiscal
  participant RUN as hr.payslip.run 🔒
  participant ACC as account.move
  participant DEC as l10n_ga.declaration
  participant REG as Registre générateurs
  participant G as GenID10
  participant CHK as Contrôles
  participant XL as XlsxRenderer / PdfRenderer
  CPT->>RUN: Valider le lot (action_validate)
  RUN->>ACC: créer l'écriture de paie (hr_payroll_account)
  RUN->>DEC: _l10n_ga_notify_payslips_done() → brouillon ID10 du mois de paiement
  DF->>DEC: action_compute()
  DEC->>REG: _get("ID10")
  REG-->>DEC: GenID10
  DEC->>G: collect(bulletins payés entre date_from et date_to)
  G-->>DEC: Facts (Σ IRPP, TCS, FNH, base CFP, détail par salarié)
  DEC->>G: fill(facts) → cases L40..L43, R49..R56
  DEC->>CHK: checks(facts)
  CHK-->>DEC: anomalies (bloquantes / avertissements)
  DF->>DEC: action_validate()
  alt anomalie bloquante
    DEC-->>DF: refus + liste des anomalies
  else aucune anomalie bloquante
    DEC->>DEC: figer lignes + détails (instantané)
    DEC->>XL: render(decl)
    XL-->>DEC: ID10.xlsx + ID10.pdf (pièces jointes)
    DEC-->>DF: état « validée »
  end
  DF->>DEC: action_mark_filed(date, n° quittance)
  DF->>DEC: ajouter quittance(s) (n°, montant, RS / FNH, écriture)
  DEC->>DEC: état « payée » quand Σ quittances = total dû
```

## 6. Séquence — DAS annuelle

```mermaid
sequenceDiagram
  autonumber
  actor DF as Déclarant fiscal
  participant W as Assistant DAS
  participant DEC as l10n_ga.declaration (DAS)
  participant G as GenDAS
  participant ID10 as Déclarations ID10 de l'année
  participant GF as GenID23/24/26 (dgi_edi_account)
  participant XL as Rendus
  DF->>W: Exercice N
  W->>DEC: créer DAS N (01/01 → 31/12)
  DEC->>G: collect(bulletins validés de l'année)
  G->>G: agréger par salarié (colonnes 1 à 11, indemnités non imposables)
  G->>G: classer ID20 (< 1 M / ≥ 1 M) et sélectionner ID19 (> 80 000/mois)
  G->>ID10: lire les quittances des ID10 (grille ID22)
  G-->>DEC: lignes ID20, ID21, ID22 + détails ID19
  DEC->>GF: collect(factures fournisseurs payées, retenues 9,5 % / 20 %)
  GF-->>DEC: ID23 (A/B/C), ID24 (CEMAC / hors CEMAC), ID26 + ID19 non-salariés
  DEC->>DEC: contrôles : Σ ID21 = Σ ID10, salariés manquants, parts incohérentes
  DF->>DEC: valider
  DEC->>XL: remplir les classeurs officiels .xlsm (openpyxl, macros conservées)
  XL-->>DF: ID19 à ID26 en .xlsm + PDF
```

## 7. Séquence — import des variables mensuelles (F3)

```mermaid
sequenceDiagram
  autonumber
  actor GP as Gestionnaire paie
  participant W as Assistant d'import
  participant X as openpyxl
  participant V as Validation (filtres)
  participant IN as hr.payslip.input 🔒
  participant WE as hr.work.entry
  participant RUN as hr.payslip.run 🔒
  GP->>W: Télécharger le modèle du lot
  W-->>GP: Excel : 1 ligne par salarié, 1 colonne par type d'entrée et d'heures
  GP->>W: Déposer le fichier rempli
  W->>X: lire les lignes
  X-->>W: valeurs brutes
  W->>V: matricule connu, type actif, nombre valide, salarié dans le lot
  V-->>W: lignes valides + anomalies
  W-->>GP: aperçu des anomalies
  GP->>W: Confirmer l'import
  W->>IN: créer / remplacer les entrées du lot
  W->>WE: créer les prestations d'heures supplémentaires (décimales)
  W->>RUN: recalculer le lot
```

## 8. Séquence — bascule depuis hr_payroll_gb (F12)

```mermaid
sequenceDiagram
  autonumber
  actor ADM as Administrateur
  participant MIG as l10n_ga_hr_payroll_migration
  participant MAP as l10n_ga.migration.map
  participant GB as Tables hr_payroll_gb (SQL)
  participant ODOO as hr.version / loans / ytd.opening
  participant DGI as l10n_ga_dgi_edi 19.0.2
  ADM->>MIG: Lancer la reprise (date de bascule)
  MIG->>MAP: charger les correspondances codes et catégories
  MIG->>GB: lire salariés, catégories, prêts, bulletins de l'année
  MIG->>ODOO: créer ou mettre à jour versions, grades, prêts en cours
  MIG->>ODOO: créer les cumuls d'ouverture de l'année
  MIG-->>ADM: rapport de rapprochement (écarts par salarié et rubrique)
  ADM->>DGI: Mettre à jour le module (scripts migrations/19.0.2.0.0)
  DGI->>DGI: convertir dgi.id10 / id20 / id22 / dts / edi.declaration
  DGI-->>ADM: déclarations V1 figées, quittances et pièces jointes reprises
```

## 9. Diagramme d'états — prêt salarié (F1)

```mermaid
stateDiagram-v2
  [*] --> brouillon
  brouillon --> approuve : action_approve [éligible ou dérogation RH]
  brouillon --> annule
  approuve --> en_cours : 1re échéance retenue sur un bulletin validé
  en_cours --> en_cours : échéance retenue / reportée
  en_cours --> solde : dernière échéance retenue
  en_cours --> solde : départ du salarié (retenue sur solde de tout compte)
  solde --> [*]
  annule --> [*]
```

## 10. Diagramme d'états — déclaration

```mermaid
stateDiagram-v2
  [*] --> brouillon : création (cron J-10 ou manuelle)
  brouillon --> calculee : action_compute
  calculee --> calculee : recalcul (bulletin modifié)
  calculee --> brouillon : reset
  calculee --> validee : action_validate [aucune anomalie bloquante]
  validee --> deposee : action_mark_filed (date, n° de dépôt)
  deposee --> payee : quittances enregistrées = total dû
  validee --> calculee : annuler la validation [droit Déclarant]
  deposee --> rectificative : créer une déclaration rectificative
  rectificative --> [*]
  payee --> [*]
  note right of validee
    Instantané figé : lignes, détails,
    fichiers Excel/PDF joints.
    Les bulletins ne peuvent plus
    modifier cette déclaration.
  end note
```

## 11. Diagramme d'activités — calcul fiscal d'un bulletin (noyau)

```mermaid
flowchart LR
  subgraph COL1["1. Assiettes et cotisations"]
    direction TB
    A([Début]) --> B[Somme des gains du mois]
    B --> C[Assiette sociale = gains soumis<br/>+ excédent transport/véhicule/carburant > 35 000]
    C --> D{Assiette < SMIG × présence ?}
    D -- oui --> D1[Assiette = SMIG proratisé]
    D -- non --> E[CNSS sal 5 % et CNAMGS sal 2 %<br/>sous plafonds 1,5 M / 2,5 M]
    D1 --> E
    E --> F[Brut imposable = gains − exonérations<br/>91 bis plafonnées, gratifications sous cumul 4 M]
  end
  subgraph COL2["2. Impôts"]
    direction TB
    G[Base TCS = brut imposable − cotisations salariales] --> H[TCS = 5 % × max 0, base − 150 000]
    H --> I[Base IRPP annualisée = base TCS − TCS × 12]
    I --> J[Abattement 20 % plafonné 10 M]
    J --> K[Q = RNI / parts de la version en vigueur]
    K --> L[Impôt 1 part = taux × Q − N]
    L --> M[IRPP mensuel = impôt × parts / 12]
  end
  subgraph COL3["3. Fin de calcul"]
    direction TB
    N{Décembre ou sortie ?} -- oui --> N1[Régularisation : IRPP annuel réel − cumul retenu]
    N -- non --> O[Charges patronales : CNSS 18 %, CNAMGS 4,1 %,<br/>FNH 3 %, CFP 0,5 %]
    N1 --> O
    O --> R{Paiement en espèces ?}
    R -- oui --> R1[NET + reliquat précédent<br/>arrondi à 500 inférieur,<br/>nouveau reliquat stocké]
    R -- non --> P([Fin : PayResult])
    R1 --> P
  end
  COL1 --> COL2
  COL2 --> COL3
```
