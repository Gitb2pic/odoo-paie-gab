class DeclarationBuilder:
    """Interface commune des rendus Excel : on écrit des valeurs, jamais de formules."""

    def header(self, values):
        """En-tête : ``{libellé ou cellule: valeur}``."""
        raise NotImplementedError  # interface abstraite (patron 9)

    def boxes(self, *args):
        """Valeurs des cases."""
        raise NotImplementedError  # interface abstraite (patron 9)

    def table(self, sheet, start_row, rows, headers=()):
        """Tableau de lignes (détails, grilles paginées) à partir de ``start_row`` (0 = première ligne)."""
        raise NotImplementedError  # interface abstraite (patron 9)

    def build(self):
        """Contenu binaire du classeur."""
        raise NotImplementedError  # interface abstraite (patron 9)
