class CalcBlock:
    """
    Generell blockklass för beräkningsdata.

    Klassen tar emot en ``details``-dictionary från en beräkningsfunktion och
    förbereder LaTeX-block för metodbeskrivning, indata, delresultat,
    slutresultat och ekvationer. All presentationsmetadata hämtas ur
    ``details`` så att klassen kan användas tillsammans med godtyckliga
    beräkningsfunktioner som följer samma struktur.
    """

    def __init__(self, details):
        """
        Initierar ett CalcBlock-objekt.

        Parametrar:
            details : dict
                Standardiserad dictionary med sektioner som innehåller ``title``
                och ``items``.
        """
        self.details = details
        self.latex = None
        self.latex_mb = None
        self.latex_id = None
        self.latex_dr = None
        self.latex_sr = None
        self.latex_ekv = None

    def _escape_text(self, text):
        """
        Escapar vanlig text för säker LaTeX-rendering i textläge.

        Parametrar:
            text : str
                Text som ska kunna renderas inne i ``\text{...}``.

        Returvärde:
            str
                Escapad text.
        """
        escaped = str(text)
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
        }
        for old, new in replacements.items():
            escaped = escaped.replace(old, new)
        return escaped

    def _wrap_text(self, text, width=85):
        """
        Delar upp text i kortare rader för stabil notebook-rendering.

        Parametrar:
            text : str
                Text som ska radbrytas.

            width : int, optional
                Ungefärlig maxlängd per rad.

        Returvärde:
            list[str]
                Lista av textlinjer.
        """
        import textwrap

        return textwrap.wrap(str(text), width=width, break_long_words=False, break_on_hyphens=False)

    def _sanera_for_katex(self, latex):
        """
        Förenklar vissa LaTeX-konstruktioner för bättre KaTeX-stöd i VSCode.

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

    def _fmt(self, value, decimals=3):
        """
        Formaterar ett numeriskt värde till sträng med valt antal decimaler.

        Parametrar:
            value : float | int | str
                Värde som ska formateras.

            decimals : int, optional
                Antal decimaler i utskriften för numeriska värden.

        Returvärde:
            str
                Formaterat värde som sträng.
        """
        if isinstance(value, (int, float)):
            return f"{value:.{decimals}f}"
        return str(value)

    def _get_item_decimals(self, item, decimals_override=None):
        """
        Hämtar antal decimaler för en datapost, med stöd för tillfällig override.

        Parametrar:
            item : dict
                Datapost med minst nyckeln ``namn``.

            decimals_override : dict[str, int] | None, optional
                Valfri dictionary där nyckeln är attributnamn och värdet är
                önskat antal decimaler för just den aktuella utskriften.

        Returvärde:
            int
                Antal decimaler som ska användas.
        """
        namn = item.get("namn", "")
        if decimals_override and namn in decimals_override:
            return decimals_override[namn]
        return self._decimals_for_item(item)

    def _decimals_for_item(self, item):
        """
        Bestämmer lämpligt antal decimaler för en datapost.

        Parametrar:
            item : dict
                Datapost med metadata för presentation.

        Returvärde:
            int
                Antal decimaler som ska användas.
        """
        if item.get("decimals") is not None:
            return item["decimals"]

        value = item.get("value")
        unit = item.get("unit", "")

        if not isinstance(value, (int, float)):
            return 0

        if not unit:
            return 3

        if unit == "kN":
            return 1

        if unit == "mm":
            if float(value).is_integer():
                return 0
            return 1

        if unit == "mm^2":
            return 0

        if unit in {"MPa", "GPa"}:
            if float(value).is_integer():
                return 0
            return 1

        return 3

    def _format_scientific(self, value, decimals=3):
        """
        Formaterar ett numeriskt värde i tiopotensform.

        Parametrar:
            value : float | int
                Numeriskt värde som ska formateras.

            decimals : int, optional
                Antal decimaler för mantissan.

        Returvärde:
            str
                LaTeX-formaterad sträng i formen ``a \\cdot 10^{n}``.
        """
        if value == 0:
            return "0"

        exponent = int(f"{value:e}".split("e")[1])
        mantissa = value / (10 ** exponent)
        mantissa_str = f"{mantissa:.{decimals}f}"
        return mantissa_str + r" \cdot 10^{" + str(exponent) + "}"

    def _format_unit(self, unit):
        """
        Formaterar enhetstext till LaTeX-vänlig notation.

        Parametrar:
            unit : str
                Enhet i enkel textform, till exempel ``mm^4``.

        Returvärde:
            str
                LaTeX-formaterad enhet.
        """
        if not unit:
            return ""

        if "^" in unit:
            bas, exponent = unit.split("^", 1)
            return r"\tiny{[\mathrm{" + bas + "}^{"+ exponent + "}]} "

        return r"\tiny{[\mathrm{" + unit + "}]} "

    def _format_value(self, item, decimals_override=None):
        """
        Formaterar högerledet för en datapost.

        Parametrar:
            item : dict
                Datapost med nycklar som ``value`` och eventuellt ``unit``.

            decimals_override : dict[str, int] | None, optional
                Valfri dictionary som tillfälligt överstyr antal decimaler för
                specifika attributnamn.

        Returvärde:
            str
                Formaterat högerled i LaTeX-vänlig textform.
        """
        value = item["value"]
        if isinstance(value, str):
            if item.get("unit"):
                return value + r"\ " + self._format_unit(item["unit"])
            return r"\text{" + value + "}"

        decimals = self._get_item_decimals(item, decimals_override=decimals_override)

        if item.get("unit") == "mm^4":
            formatted = self._format_scientific(value, decimals=decimals)
        else:
            formatted = self._fmt(value, decimals)
        if item.get("unit"):
            return formatted + r"\ " + self._format_unit(item["unit"])
        return formatted

    def _format_etikett(self, text):
        """
        Formaterar etiketttext för något mindre visuell tyngd.

        Parametrar:
            text : str
                Etiketttext som ska visas i utskriften.

        Returvärde:
            str
                LaTeX-kod för etiketten.
        """
        return r"\tiny{\text{" + text + r"}}"

    def _dela_items_i_kolumner(self, items, rader=None):
        """
        Delar upp en lista av poster i interna kolumner.

        Parametrar:
            items : list[dict]
                Poster som ska fordela sig over en eller flera kolumner.

            rader : int | None, optional
                Maximalt antal rader per intern kolumn. Om ``None`` eller ett
                icke-positivt varde anges anvands en enda kolumn utan maxtak.

        Returvarde:
            list[list[dict]]
                En lista av kolumner dar varje kolumn innehaller sina poster.
        """
        if rader is None or rader <= 0:
            return [items]

        return [items[i:i + rader] for i in range(0, len(items), rader)]

    def _array_colspec(self, antal_kolumner, etikettkolumn=True):
        """
        Bygger en KaTeX-kompatibel kolumnspec för ``array``.

        VSCode:s notebook-rendering via KaTeX stöder inte LaTeX-justeringar av
        typen ``@{...}``, så vi håller oss till enkla kolumnmarkörer.

        Parametrar:
            antal_kolumner : int
                Antal interna datakolumner i blocket.

            etikettkolumn : bool, optional
                Om True inkluderas den fjärde kolumnen för etiketttext.

        Returvärde:
            str
                Kolumnspec för ``array``.
        """
        baskolumner = "lcll" if etikettkolumn else "lcl"
        return baskolumner * antal_kolumner

    def _vansterjusterat_array(self, colspec):
        """
        Bygger startsträngen för ett ``array`` utan synlig vänstermarginal.

        När ``@{}`` inte används lägger ``array`` in standardluft till vänster.
        En liten negativ horizontalspacer neutraliserar detta och fungerar i
        både notebook och KaTeX/VSCode.

        Parametrar:
            colspec : str
                Kolumnspec för arraymiljön.

        Returvärde:
            str
                Startsträng för arraymiljön.
        """
        return r"\hspace{-0.6em}\begin{array}{" + colspec + "}"

    def _build_section_block(self, section, etikett=False, decimals=None, rader=None):
        """
        Bygger ett LaTeX-block för en sektion som innehåller dataposter.

        Parametrar:
            section : dict
                Sektion med ``title`` och ``items``.

            etikett : bool, optional
                Om True läggs förklarande etiketter till.

            decimals : dict[str, int] | None, optional
                Valfri dictionary för tillfällig override av antal decimaler
                per attributnamn i den aktuella utskriften.

            rader : int | None, optional
                Maximalt antal rader per intern kolumn. Om ``None`` används
                ingen uppdelning i flera kolumner.

        Returvärde:
            str
                LaTeX-kod för sektionen.
        """
        kolumner = self._dela_items_i_kolumner(section["items"], rader=rader)

        lines = [r"$"]
        lines.append(self._vansterjusterat_array("l"))
        lines.append(r"\textbf{" + section["title"] + r"}\\")
        colspec = self._array_colspec(len(kolumner))
        lines.append(self._vansterjusterat_array(colspec))

        max_rader = max(len(kolumn) for kolumn in kolumner)
        for radindex in range(max_rader):
            radceller = []
            for kolumn in kolumner:
                if radindex < len(kolumn):
                    item = kolumn[radindex]
                    lhs = item["latex"]
                    rhs = self._format_value(item, decimals_override=decimals)
                    kommentar = (
                        self._format_etikett(item["etikett"])
                        if etikett and item.get("etikett")
                        else ""
                    )
                    radceller.extend([lhs, "=", rhs, kommentar])
                else:
                    radceller.extend(["", "", "", ""])
            lines.append(" & ".join(radceller) + r"\\")

        lines.append(r"\end{array}")
        lines.append(r"\end{array}")
        lines.append(r"$")
        return "\n".join(lines)

    def _build_equation_block(self, section, etikett=False, rader=None):
        """
        Bygger ett LaTeX-block för en sektion som innehåller ekvationer.

        Parametrar:
            section : dict
                Sektion med ``title`` och ``items``.

            etikett : bool, optional
                Om True läggs förklarande etiketter till under ekvationerna.

            rader : int | None, optional
                Maximalt antal rader per intern kolumn. Om ``None`` används
                ingen uppdelning i flera kolumner.

        Returvärde:
            str
                LaTeX-kod för ekvationssektionen.
        """
        kolumner = self._dela_items_i_kolumner(section["items"], rader=rader)

        lines = [r"$"]
        lines.append(self._vansterjusterat_array("l"))
        lines.append(r"\textbf{" + section["title"] + r"}\\")
        colspec = self._array_colspec(len(kolumner))
        lines.append(self._vansterjusterat_array(colspec))

        max_rader = max(len(kolumn) for kolumn in kolumner)
        for radindex in range(max_rader):
            radceller = []
            for kolumn in kolumner:
                if radindex < len(kolumn):
                    item = kolumn[radindex]
                    kommentar = (
                        self._format_etikett(item["etikett"])
                        if etikett and item.get("etikett")
                        else ""
                    )
                    uttryck = item["latex"]
                    if "=" in uttryck:
                        vanster, hoger = uttryck.split("=", 1)
                        vanster = vanster.strip()
                        hoger = hoger.strip()
                    else:
                        vanster = uttryck
                        hoger = ""
                    radceller.extend([vanster, "=", hoger, kommentar])
                else:
                    radceller.extend(["", "", "", ""])
            lines.append(" & ".join(radceller) + r"\\")

        lines.append(r"\end{array}")
        lines.append(r"\end{array}")
        lines.append(r"$")
        return "\n".join(lines)

    def _build_method_block(self, section):
        """
        Bygger ett LaTeX-block för metodbeskrivning.

        Parametrar:
            section : dict
                Sektion med ``title`` och ``items`` där varje post innehåller
                ``rubrik`` och ``text``.

        Returvärde:
            str
                LaTeX-kod för metodbeskrivningen.
        """
        lines = [r"$", r"\begin{aligned}"]
        lines.append(r"& \textbf{" + self._escape_text(section["title"]) + r"} \\[0.4em]")

        for index, item in enumerate(section["items"]):
            rubrik = self._escape_text(item.get("rubrik", ""))
            text = item.get("text", "")
            textlinjer = self._wrap_text(text)

            lines.append(r"& \textbf{" + rubrik + r"} \\")
            for rad in textlinjer:
                lines.append(r"& \text{" + self._escape_text(rad) + r"} \\")

            if index < len(section["items"]) - 1:
                lines.append(r"& \\[0.35em]")

        lines.append(r"\end{aligned}")
        lines.append(r"$")
        return "\n".join(lines)

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

        latex = self._sanera_for_katex(latex)
        display(Latex(latex))

    def ID(self, visa=False, etikett=False, decimals=None, rader=None):
        """
        Förbereder LaTeX-block för indata.

        Parametrar:
            visa : bool, optional
                Om True renderas blocket direkt i notebook.

            etikett : bool, optional
                Om True läggs förklarande etiketter till för varje storhet.

            decimals : dict[str, int] | None, optional
                Tillfällig override av antal decimaler för specifika attribut.
                Exempel: ``cp.ID(decimals={"beta": 1, "gamma_M": 2})``.

            rader : int | None, optional
                Maximalt antal rader per intern kolumn. Om ``None`` används
                en enda kolumn utan maxtak.
        """
        self.latex_id = self._build_section_block(
            self.details["indata"], etikett=etikett, decimals=decimals, rader=rader
        )
        self.latex = self.latex_id
        if visa:
            self._visa(self.latex_id)

    def MB(self, visa=False):
        """
        Förbereder LaTeX-block för metodbeskrivning.

        Parametrar:
            visa : bool, optional
                Om True renderas blocket direkt i notebook.
        """
        self.latex_mb = self._build_method_block(self.details["metodbeskrivning"])
        self.latex = self.latex_mb
        if visa:
            self._visa(self.latex_mb)

    def DR(self, visa=False, etikett=False, decimals=None, rader=None):
        """
        Förbereder LaTeX-block för delresultat.

        Parametrar:
            visa : bool, optional
                Om True renderas blocket direkt i notebook.

            etikett : bool, optional
                Om True läggs förklarande etiketter till för varje storhet.

            decimals : dict[str, int] | None, optional
                Tillfällig override av antal decimaler för specifika attribut.
                Exempel: ``cp.DR(decimals={"lambda": 1, "k_c": 2})``.

            rader : int | None, optional
                Maximalt antal rader per intern kolumn. Om ``None`` används
                en enda kolumn utan maxtak.
        """
        self.latex_dr = self._build_section_block(
            self.details["delresultat"], etikett=etikett, decimals=decimals, rader=rader
        )
        self.latex = self.latex_dr
        if visa:
            self._visa(self.latex_dr)

    def SR(self, visa=False, etikett=False, decimals=None, rader=None):
        """
        Förbereder LaTeX-block för slutresultat.

        Parametrar:
            visa : bool, optional
                Om True renderas blocket direkt i notebook.

            etikett : bool, optional
                Om True läggs förklarande etiketter till för varje storhet.

            decimals : dict[str, int] | None, optional
                Tillfällig override av antal decimaler för specifika attribut.
                Exempel: ``cp.SR(decimals={"N_R_d": 2})``.

            rader : int | None, optional
                Maximalt antal rader per intern kolumn. Om ``None`` används
                en enda kolumn utan maxtak.
        """
        self.latex_sr = self._build_section_block(
            self.details["slutresultat"], etikett=etikett, decimals=decimals, rader=rader
        )
        self.latex = self.latex_sr
        if visa:
            self._visa(self.latex_sr)

    def EKV(self, visa=False, etikett=False, decimals=None, rader=None):
        """
        Förbereder LaTeX-block för använda ekvationer.

        Parametrar:
            visa : bool, optional
                Om True renderas blocket direkt i notebook.

            etikett : bool, optional
                Om True läggs förklarande etiketter till under ekvationerna.

            decimals : dict[str, int] | None, optional
                Medtas för konsekvent gränssnitt. Parametern används inte för
                ekvationsutskriften eftersom ekvationerna inte formatteras via
                numeriska värden.

            rader : int | None, optional
                Maximalt antal rader per intern kolumn. Om ``None`` används
                en enda kolumn utan maxtak.
        """
        self.latex_ekv = self._build_equation_block(
            self.details["ekvationer"], etikett=etikett, rader=rader
        )
        self.latex = self.latex_ekv
        if visa:
            self._visa(self.latex_ekv)
