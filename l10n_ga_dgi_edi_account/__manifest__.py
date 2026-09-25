{
    'name': 'Gabon - Déclarations DGI de la comptabilité (V1.0)',
    'version': '19.0.1.0.0',
    'summary': 'Retenues 9,5 % et 20 % au paiement, ID18, ID27, annexes DAS ID23, ID24, ID26',
    'countries': ['ga'],
    'category': 'Accounting/Localizations',
    'author': 'OMIAS Leadership Group',
    'maintainer': 'MPAMI MPAMI Nathan Mael Alex',
    # Périmètre V1.0 (ADR-13, F9) : CA01, ID30, ID09, ID31, IS, patente et CFU relèvent de la V2.0.
    'depends': ['l10n_ga_dgi_edi', 'l10n_ga', 'l10n_account_withholding_tax'],
    'data': [
        'data/l10n_ga_declaration_type_data.xml',
        'views/res_partner_views.xml',
        'views/account_tax_views.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'license': 'OPL-1',
}
