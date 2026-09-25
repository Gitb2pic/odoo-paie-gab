"""Rendus Excel des déclarations (patron 9 « Builder », F10, règle d'or 10).

Deux moteurs derrière la même interface :class:`DeclarationBuilder` : ``xlsxwriter`` pour les
classeurs neufs, ``openpyxl`` (``keep_vba=True``) pour remplir les gabarits officiels ``.xlsm``.
Aucun accès à l’ORM : les valeurs arrivent déjà lues sur les champs stockés.
"""
