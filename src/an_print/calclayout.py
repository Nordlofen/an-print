class CalcLayout:
    """
    Layoutklass för att arrangera genererade LaTeX-block från ett eller flera
    CalcBlock-objekt i ett gemensamt rutnät.

    Klassen känner inte till någon specifik beräkningstyp. Den arbetar enbart
    med redan genererade block som hämtas från attribut i CalcBlock-objekt,
    till exempel ``latex_mb``, ``latex_id``, ``latex_dr``, ``latex_sr`` och
    ``latex_ekv``.
    """

    def __init__(self):
        """
        Initierar ett CalcLayout-objekt.
        """
        pass

    def _strip_math_wrappers(self, latex):
        """
        Tar bort omgivande dollartecken från ett block för layoutsammanfogning.

        Parametrar:
            latex : str
                LaTeX-sträng för ett enskilt block.

        Returvärde:
            str
                Innehållet utan yttre dollartecken.
        """
        cleaned = latex.strip()
        if cleaned.startswith("$"):
            cleaned = cleaned[1:]
        if cleaned.endswith("$"):
            cleaned = cleaned[:-1]
        return cleaned.strip()

    def _visa(self, latex):
        """
        Visar en LaTeX-sträng i notebookmiljö.

        Parametrar:
            latex : str
                LaTeX-kod som ska renderas.
        """
        try:
            from IPython.display import Latex, display
        except ModuleNotFoundError:
            return

        display(Latex(latex))

    def _array_colspec(self, antal_kolumner):
        """
        Bygger en enkel KaTeX-kompatibel kolumnspec för layoutmatrisen.

        VSCode:s KaTeX-renderare stöder inte ``@{}`` i ``array``-kolumnspecen,
        så layouten använder endast enkla vänsterjusterade kolumner.

        Parametrar:
            antal_kolumner : int
                Antal kolumner i layouten.

        Returvärde:
            str
                Kolumnspec för ``array``.
        """
        return "l" * antal_kolumner

    def _hamta_block(self, calcblock_objekt, blocknamn):
        """
        Hämtar ett redan genererat block från ett CalcBlock-objekt.

        Parametrar:
            calcblock_objekt : object
                Objekt som förväntas bära attribut som ``latex_mb``,
                ``latex_id``, ``latex_dr``, ``latex_sr`` eller ``latex_ekv``.

            blocknamn : str
                Ett av ``"MB"``, ``"ID"``, ``"DR"``, ``"SR"`` eller ``"EKV"``.

        Returvärde:
            str
                LaTeX-strängen för blocket.
        """
        mapping = {
            "MB": "latex_mb",
            "ID": "latex_id",
            "DR": "latex_dr",
            "SR": "latex_sr",
            "EKV": "latex_ekv",
        }

        blocknamn = blocknamn.upper()
        if blocknamn not in mapping:
            raise ValueError("blocknamn måste vara 'MB', 'ID', 'DR', 'SR' eller 'EKV'.")

        attribut = mapping[blocknamn]
        latex = getattr(calcblock_objekt, attribut, None)
        if latex is None:
            raise ValueError(
                f"Blocket {blocknamn} har inte genererats ännu på det angivna CalcBlock-objektet."
            )
        return latex

    def render(self, positions, grid=None, visa=True):
        """
        Arrangerar block från ett eller flera CalcBlock-objekt i ett rutnät.

        Parametrar:
            positions : dict[tuple[object, str] | str, tuple[int, int]]
                Mapping mellan block och positioner. Nyckeln kan vara:
                - ett blocknamn som ``\"ID\"`` om ett och samma CalcBlock-objekt används
                  konsekvent i anropet via tuple-format
                - en tuple ``(calcblock_objekt, blocknamn)`` för explicit kontroll

                Rekommenderat format är:
                ``{(cb1, "ID"): (0, 0), (cb1, "DR"): (0, 1), (cb2, "SR"): (1, 0)}``

            grid : tuple[int, int] | None, optional
                Storlek på rutnätet som ``(antal_rader, antal_kolumner)``.
                Om ``None`` bestäms storleken automatiskt från ``positions``.

            visa : bool, optional
                Om True renderas layouten direkt i notebook.

        Returvärde:
            None
                Metoden renderar layouten direkt och returnerar inget värde.
        """
        if not positions:
            raise ValueError("positions får inte vara tom.")

        for key in positions:
            if not isinstance(key, tuple) or len(key) != 2:
                raise ValueError(
                    "Varje nyckel i positions måste vara en tuple på formen (calcblock_objekt, blocknamn)."
                )

        min_rad = min(rad for rad, _ in positions.values())
        min_kol = min(kol for _, kol in positions.values())
        normaliserade_positioner = {
            key: (rad - min_rad, kol - min_kol)
            for key, (rad, kol) in positions.items()
        }

        if grid is None:
            max_rad = max(rad for rad, _ in normaliserade_positioner.values())
            max_kol = max(kol for _, kol in normaliserade_positioner.values())
            rows = max_rad + 1
            cols = max_kol + 1
        else:
            rows, cols = grid

        matris = [["" for _ in range(cols)] for _ in range(rows)]

        for (calcblock_objekt, blocknamn), (rad, kol) in normaliserade_positioner.items():
            if not (0 <= rad < rows and 0 <= kol < cols):
                raise ValueError(f"Positionen för {blocknamn} ligger utanför angivet rutnät.")
            latex = self._hamta_block(calcblock_objekt, blocknamn)
            matris[rad][kol] = self._strip_math_wrappers(latex)

        colspec = self._array_colspec(cols)
        lines = [r"$"]
        lines.append(r"\begin{array}{" + colspec + "}")
        for rad in range(rows):
            radceller = []
            for kol in range(cols):
                cell = matris[rad][kol]
                if cell:
                    radceller.append(r"\begin{array}[t]{l}" + cell + r"\end{array}")
                else:
                    radceller.append("")
            lines.append(" & ".join(radceller) + r"\\[1em]")
        lines.append(r"\end{array}")
        lines.append(r"$")

        latex = "\n".join(lines)
        if visa:
            self._visa(latex)
        return None
