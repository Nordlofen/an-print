class CalcLayout:
    """
    Layoutklass för att arrangera genererade block från ett eller flera
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
        Tar bort omgivande dollartecken från ett block för vidare rendering.

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

    def _sanera_for_katex(self, latex):
        """
        Förenklar vissa LaTeX-konstruktioner för bättre KaTeX-stöd.

        Parametrar:
            latex : str
                LaTeX-sträng som ska saneras.

        Returvärde:
            str
                KaTeX-vänligare LaTeX-sträng.
        """
        import re

        latex = re.sub(r"@\{[^}]*\}", "", latex)
        latex = re.sub(r"\\begin\{array\}\[[^\]]*\]", r"\\begin{array}", latex)
        return latex

    def _visa_latex(self, latex):
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

        latex = self._sanera_for_katex(latex)
        display(Latex(latex))

    def _visa_html(self, html):
        """
        Visar en HTML-sträng i notebookmiljö.

        Parametrar:
            html : str
                HTML-kod som ska renderas.
        """
        try:
            from IPython.display import HTML, display
        except ModuleNotFoundError:
            return

        display(HTML(html))

    def _array_colspec(self, antal_kolumner):
        """
        Bygger en enkel KaTeX-kompatibel kolumnspec för layoutmatrisen.

        Parametrar:
            antal_kolumner : int
                Antal kolumner i layouten.

        Returvärde:
            str
                Kolumnspec för ``array``.
        """
        return "l" * antal_kolumner

    def _array_start(self, colspec):
        """
        Bygger startsträngen för ett ``array``.

        Parametrar:
            colspec : str
                Kolumnspec för arraymiljön.

        Returvärde:
            str
                Startsträng för arraymiljön.
        """
        return r"\begin{array}{" + colspec + "}"

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
                Blockets LaTeX-sträng.
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

    def _hamta_html_block(self, calcblock_objekt, blocknamn):
        """
        Hämtar ett redan genererat HTML-block från ett CalcBlock-objekt.

        Parametrar:
            calcblock_objekt : object
                Objekt som förväntas bära HTML-attribut för blocket.

            blocknamn : str
                Ett av ``"MB"``, ``"ID"``, ``"DR"``, ``"SR"`` eller ``"EKV"``.

        Returvärde:
            str
                Blockets HTML-sträng.
        """
        mapping = {
            "MB": "html_mb",
            "ID": "html_id",
            "DR": "html_dr",
            "SR": "html_sr",
            "EKV": "html_ekv",
        }

        blocknamn = blocknamn.upper()
        if blocknamn not in mapping:
            raise ValueError("blocknamn måste vara 'MB', 'ID', 'DR', 'SR' eller 'EKV'.")

        attribut = mapping[blocknamn]
        html_block = getattr(calcblock_objekt, attribut, None)
        if html_block is None:
            raise ValueError(
                f"HTML-rendering för blocket {blocknamn} finns inte ännu på det angivna "
                f"CalcBlock-objektet. Bygg blocket först och använd bara blocktyper med HTML-stöd."
            )
        return html_block

    def _normalisera_positions(self, positions, grid=None):
        """
        Validerar och normaliserar positioner till ett rutnät med nollindex.

        Parametrar:
            positions : dict[tuple[object, str], tuple[int, int]]
                Mapping mellan block och rutnätspositioner.

            grid : tuple[int, int] | None, optional
                Storlek på rutnätet som ``(antal_rader, antal_kolumner)``.

        Returvärde:
            tuple[dict, int, int]
                Normaliserade positioner samt antal rader och kolumner.
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

        for (_, blocknamn), (rad, kol) in normaliserade_positioner.items():
            if not (0 <= rad < rows and 0 <= kol < cols):
                raise ValueError(f"Positionen för {blocknamn} ligger utanför angivet rutnät.")

        return normaliserade_positioner, rows, cols

    def _bygg_html(self, positions, rows, cols):
        """
        Bygger HTML/CSS-layout för redan genererade block.

        Parametrar:
            positions : dict[tuple[object, str], tuple[int, int]]
                Normaliserade positioner för blocken.

            rows : int
                Antal rader i layouten.

            cols : int
                Antal kolumner i layouten.

        Returvärde:
            str
                HTML-sträng för layouten.
        """
        style = f"""
<style>
.anp-layout {{
  display: grid;
  grid-template-columns: repeat({cols}, minmax(0, 1fr));
  gap: 1rem 1.5rem;
  align-items: start;
  margin: 0;
  padding: 0;
  width: 100%;
}}

.anp-layout__cell {{
  min-width: 0;
  margin: 0;
  padding: 0;
}}

.anp-layout__block {{
  margin: 0;
  padding: 0;
}}

.anp-method-block {{
  margin: 0;
  padding: 0;
}}

.anp-method-block__title {{
  margin: 0 0 0.75rem;
  font-size: 1.15rem;
  font-weight: 700;
}}

.anp-method-block__item + .anp-method-block__item {{
  margin-top: 1rem;
}}

.anp-method-block__heading {{
  margin: 0 0 0.35rem;
  font-size: 1rem;
  font-weight: 700;
}}

.anp-method-block__text {{
  margin: 0;
  line-height: 1.45;
  white-space: normal;
}}

.anp-data-block {{
  margin: 0;
  padding: 0;
}}

.anp-data-block__title {{
  margin: 0 0 0.6rem;
  font-size: 1.05rem;
  font-weight: 700;
}}

.anp-data-block__columns {{
  display: grid;
  grid-template-columns: repeat(var(--anp-cols), minmax(0, 1fr));
  gap: 0.75rem 1.5rem;
  align-items: start;
}}

.anp-data-block__column {{
  min-width: 0;
}}

.anp-data-block__row {{
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr);
  gap: 0.25rem 0.5rem;
  align-items: baseline;
  margin: 0 0 0.2rem;
}}

.anp-data-block__eq {{
  opacity: 0.75;
}}

.anp-data-block__lhs {{
  font-style: italic;
  white-space: nowrap;
}}

.anp-data-block__rhs {{
  min-width: 0;
  white-space: nowrap;
}}

.anp-data-block__unit {{
  opacity: 0.7;
  font-size: 0.82em;
  white-space: nowrap;
}}

.anp-data-block__etikett {{
  grid-column: 3;
  margin-top: -0.05rem;
  opacity: 0.72;
  font-size: 0.8em;
}}

.anp-frac {{
  display: inline-grid;
  grid-template-rows: auto auto;
  justify-items: center;
  align-items: center;
  vertical-align: middle;
  line-height: 1.05;
  margin: 0 0.08em;
}}

.anp-frac__num {{
  display: block;
  padding: 0 0.18em 0.06em;
  border-bottom: 0.08em solid currentColor;
}}

.anp-frac__den {{
  display: block;
  padding: 0.06em 0.18em 0;
}}

.anp-sqrt {{
  display: inline-flex;
  align-items: flex-start;
  vertical-align: middle;
}}

.anp-sqrt__sign {{
  font-size: 1.15em;
  line-height: 1;
  padding-right: 0.04em;
}}

.anp-sqrt__body {{
  border-top: 0.08em solid currentColor;
  padding: 0.02em 0 0 0.08em;
}}

.anp-eq-block {{
  margin: 0;
  padding: 0;
}}

.anp-eq-block__title {{
  margin: 0 0 0.6rem;
  font-size: 1.05rem;
  font-weight: 700;
}}

.anp-eq-block__columns {{
  display: grid;
  grid-template-columns: repeat(var(--anp-cols), minmax(0, 1fr));
  gap: 0.9rem 1.75rem;
  align-items: start;
}}

.anp-eq-block__column {{
  min-width: 0;
}}

.anp-eq-block__row {{
  display: grid;
  grid-template-columns: minmax(0, auto) auto minmax(0, 1fr);
  gap: 0.3rem 0.55rem;
  align-items: baseline;
  margin: 0 0 0.35rem;
}}

.anp-eq-block__lhs,
.anp-eq-block__rhs {{
  white-space: nowrap;
}}

.anp-eq-block__eq {{
  opacity: 0.75;
}}

.anp-eq-block__etikett {{
  grid-column: 3;
  margin-top: -0.05rem;
  opacity: 0.72;
  font-size: 0.8em;
}}

</style>
"""

        blocks = []
        for (calcblock_objekt, blocknamn), (rad, kol) in positions.items():
            html_block = self._hamta_html_block(calcblock_objekt, blocknamn)
            blocks.append(
                f"""
<div class="anp-layout__cell" style="grid-row: {rad + 1}; grid-column: {kol + 1};">
  <div class="anp-layout__block anp-layout__block--{blocknamn.lower()}">
    {html_block}
  </div>
</div>"""
            )

        return (
            style
            + f'\n<div class="anp-layout" data-rows="{rows}" data-cols="{cols}">'
            + "".join(blocks)
            + "\n</div>"
        )

    def _render_html_hybrid(self, positions, rows, cols, visa=True):
        """
        Renderar HTML-stödda block som HTML och ``EKV`` som ren LaTeX.

        I HTML-läget hålls ``EKV`` utanför HTML-kedjan för att undvika
        opålitlig MathJax-rendering i VSCode. Varje rad renderas därför för
        sig, och rader som innehåller ``EKV`` måste vara rena ekvationsrader.

        Parametrar:
            positions : dict[tuple[object, str], tuple[int, int]]
                Normaliserade positioner för blocken.

            rows : int
                Antal rader i layouten.

            cols : int
                Antal kolumner i layouten.

            visa : bool, optional
                Om True visas respektive rad direkt.
        """
        if not visa:
            return None

        for rad in range(rows):
            radposter = {
                key: (0, kol)
                for key, (row, kol) in positions.items()
                if row == rad
            }
            if not radposter:
                continue

            blocknamn_i_rad = [blocknamn.upper() for (_, blocknamn) in radposter]
            innehaller_ekv = any(blocknamn == "EKV" for blocknamn in blocknamn_i_rad)
            innehaller_ovrigt = any(blocknamn != "EKV" for blocknamn in blocknamn_i_rad)

            if innehaller_ekv and innehaller_ovrigt:
                raise ValueError(
                    "motor='html' stöder inte att EKV delar rad med andra block. "
                    "Placera EKV på egen rad eller använd motor='latex'."
                )

            if innehaller_ekv:
                rendered = self._bygg_latex(radposter, 1, cols)
                self._visa_latex(rendered)
            else:
                rendered = self._bygg_html(radposter, 1, cols)
                self._visa_html(rendered)

        return None

    def _bygg_latex(self, positions, rows, cols):
        """
        Bygger LaTeX-layout för redan genererade block.

        Parametrar:
            positions : dict[tuple[object, str], tuple[int, int]]
                Normaliserade positioner för blocken.

            rows : int
                Antal rader i layouten.

            cols : int
                Antal kolumner i layouten.

        Returvärde:
            str
                LaTeX-sträng för layouten.
        """
        matris = [["" for _ in range(cols)] for _ in range(rows)]

        for (calcblock_objekt, blocknamn), (rad, kol) in positions.items():
            latex = self._hamta_block(calcblock_objekt, blocknamn)
            latex = self._sanera_for_katex(latex)
            matris[rad][kol] = self._strip_math_wrappers(latex)

        colspec = self._array_colspec(cols)
        lines = [r"$"]
        lines.append(self._array_start(colspec))
        for rad in range(rows):
            radceller = []
            for kol in range(cols):
                cell = matris[rad][kol]
                if cell:
                    radceller.append(self._array_start("l") + cell + r"\end{array}")
                else:
                    radceller.append("")
            lines.append(" & ".join(radceller) + r"\\[1em]")
        lines.append(r"\end{array}")
        lines.append(r"$")
        return "\n".join(lines)

    def render(self, positions, grid=None, visa=True, motor="latex"):
        """
        Arrangerar block från ett eller flera CalcBlock-objekt i ett rutnät.

        Parametrar:
            positions : dict[tuple[object, str], tuple[int, int]]
                Mapping mellan block och positioner.

            grid : tuple[int, int] | None, optional
                Storlek på rutnätet som ``(antal_rader, antal_kolumner)``.
                Om ``None`` bestäms storleken automatiskt från ``positions``.

            visa : bool, optional
                Om True renderas layouten direkt i notebook.

            motor : str, optional
                ``"latex"`` för den etablerade LaTeX-baserade layouten eller
                ``"html"`` för experimentell HTML/CSS-layout.

        Returvärde:
            None
                Metoden renderar layouten direkt och returnerar inget värde.
        """
        positions, rows, cols = self._normalisera_positions(positions, grid=grid)

        if motor == "html":
            return self._render_html_hybrid(positions, rows, cols, visa=visa)

        if motor == "latex":
            rendered = self._bygg_latex(positions, rows, cols)
            if visa:
                self._visa_latex(rendered)
            return None

        raise ValueError("motor måste vara 'html' eller 'latex'.")
