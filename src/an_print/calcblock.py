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
        self.html_mb = None
        self.html_id = None
        self.html_dr = None
        self.html_sr = None
        self.html_ekv = None

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

    def _escape_html(self, text):
        """
        Escapar vanlig text för säker HTML-rendering.

        Parametrar:
            text : str
                Text som ska renderas i HTML.

        Returvärde:
            str
                Escapad text.
        """
        import html

        return html.escape(str(text), quote=True)

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
        if isinstance(value, bool):
            return "Ja" if value else "Nej"
        if isinstance(value, (int, float)):
            return f"{value:.{decimals}f}"
        return str(value)

    def _format_text_value(self, value):
        """
        Formaterar textuella värden för visning i textläge.

        Parametrar:
            value : str | bool
                Värde som ska visas.

        Returvärde:
            str
                LaTeX-säker textrepresentation.
        """
        if isinstance(value, bool):
            text = "Ja" if value else "Nej"
        else:
            text = str(value).replace("_", " ")
        return r"\text{" + self._escape_text(text) + "}"

    def _format_lhs(self, item):
        """
        Formaterar vänsterledet för en datapost.

        Parametrar:
            item : dict
                Datapost med nycklar som ``latex`` och ``value``.

        Returvärde:
            str
                LaTeX-kod för vänsterledet.
        """
        value = item.get("value")
        lhs = str(item.get("latex", ""))

        if isinstance(value, (str, bool)):
            if any(token in lhs for token in ("_", "^", "\\")):
                return lhs
            lhs_text = lhs.replace("_", " ")
            return r"\text{" + self._escape_text(lhs_text) + "}"

        return lhs

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

        if isinstance(value, bool):
            return 0

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

    def _format_scientific_html(self, value, decimals=3):
        """
        Formaterar ett numeriskt värde i tiopotensform för HTML.

        Parametrar:
            value : float | int
                Numeriskt värde som ska formateras.

            decimals : int, optional
                Antal decimaler för mantissan.

        Returvärde:
            str
                HTML-formaterad sträng i formen ``a · 10`` med exponent.
        """
        if value == 0:
            return "0"

        exponent = int(f"{value:e}".split("e")[1])
        mantissa = value / (10 ** exponent)
        mantissa_str = self._escape_html(f"{mantissa:.{decimals}f}")
        return f'{mantissa_str} &middot; 10<sup>{exponent}</sup>'

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

    def _format_unit_html(self, unit):
        """
        Formaterar enhet för HTML-visning.

        Parametrar:
            unit : str
                Enhet i enkel textform.

        Returvärde:
            str
                HTML-formaterad enhet.
        """
        if not unit:
            return ""

        if "^" in unit:
            bas, exponent = unit.split("^", 1)
            unit_html = f"{self._escape_html(bas)}<sup>{self._escape_html(exponent)}</sup>"
        else:
            unit_html = self._escape_html(unit)

        return f'<span class="anp-data-block__unit">[{unit_html}]</span>'

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
        if isinstance(value, (str, bool)):
            formatted = self._format_text_value(value)
            unit = item.get("unit", "")
            if unit and unit != "-":
                return formatted + r"\ " + self._format_unit(unit)
            return formatted

        decimals = self._get_item_decimals(item, decimals_override=decimals_override)

        if item.get("unit") == "mm^4":
            formatted = self._format_scientific(value, decimals=decimals)
        else:
            formatted = self._fmt(value, decimals)
        unit = item.get("unit", "")
        if unit and unit != "-":
            return formatted + r"\ " + self._format_unit(unit)
        return formatted

    def _format_value_html(self, item, decimals_override=None):
        """
        Formaterar högerledet för en datapost i HTML.

        Parametrar:
            item : dict
                Datapost med nycklar som ``value`` och eventuellt ``unit``.

            decimals_override : dict[str, int] | None, optional
                Valfri dictionary som tillfälligt överstyr antal decimaler.

        Returvärde:
            str
                HTML-formaterat högerled.
        """
        value = item["value"]
        if isinstance(value, (str, bool)):
            if isinstance(value, bool):
                text = "Ja" if value else "Nej"
            else:
                text = str(value).replace("_", " ")
            formatted = self._escape_html(text)
        else:
            decimals = self._get_item_decimals(item, decimals_override=decimals_override)
            if item.get("unit") == "mm^4":
                formatted = self._format_scientific_html(value, decimals=decimals)
            else:
                formatted = self._escape_html(self._fmt(value, decimals))

        unit = item.get("unit", "")
        unit_html = self._format_unit_html(unit if unit != "-" else "")
        if unit_html:
            return f'{formatted} {unit_html}'
        return formatted

    def _latex_to_html(self, latex):
        """
        Konverterar enkel inline-LaTeX till HTML utan beroende av MathJax.

        Den här vägen är avsiktligt begränsad till de uttryck som används i
        ``ID``, ``DR`` och ``SR``.

        Parametrar:
            latex : str
                Inline-LaTeX som exempelvis ``I_y`` eller ``f_{c,0,k}``.

        Returvärde:
            str
                HTML-sträng för uttrycket.
        """
        greek = {
            "alpha": "α",
            "beta": "β",
            "gamma": "γ",
            "Gamma": "Γ",
            "lambda": "λ",
            "Lambda": "Λ",
            "mu": "μ",
            "rho": "ρ",
            "sigma": "σ",
            "tau": "τ",
            "phi": "φ",
            "varphi": "φ",
            "chi": "χ",
            "psi": "ψ",
            "omega": "ω",
        }

        def skip_ws(text, idx):
            while idx < len(text) and text[idx].isspace():
                idx += 1
            return idx

        def read_command(text, idx):
            idx += 1
            start = idx
            while idx < len(text) and text[idx].isalpha():
                idx += 1
            if start == idx and idx < len(text):
                idx += 1
            return text[start:idx], idx

        def read_group(text, idx):
            idx = skip_ws(text, idx)
            if idx >= len(text):
                return "", idx
            if text[idx] == "{":
                depth = 1
                idx += 1
                start = idx
                while idx < len(text) and depth > 0:
                    if text[idx] == "{":
                        depth += 1
                    elif text[idx] == "}":
                        depth -= 1
                    idx += 1
                return text[start:idx - 1], idx
            return text[idx], idx + 1

        def render_segment(text):
            parts = []
            idx = 0
            while idx < len(text):
                char = text[idx]

                if char == "\\":
                    cmd, idx = read_command(text, idx)

                    if cmd in greek:
                        parts.append(greek[cmd])
                        continue

                    if cmd in {"left", "right"}:
                        idx = skip_ws(text, idx)
                        continue

                    if cmd == "frac":
                        num, idx = read_group(text, idx)
                        den, idx = read_group(text, idx)
                        parts.append(
                            '<span class="anp-frac">'
                            f'<span class="anp-frac__num">{render_segment(num)}</span>'
                            f'<span class="anp-frac__den">{render_segment(den)}</span>'
                            "</span>"
                        )
                        continue

                    if cmd == "sqrt":
                        body, idx = read_group(text, idx)
                        parts.append(
                            '<span class="anp-sqrt">'
                            '<span class="anp-sqrt__sign">&radic;</span>'
                            f'<span class="anp-sqrt__body">{render_segment(body)}</span>'
                            "</span>"
                        )
                        continue

                    if cmd in {"mathrm", "text"}:
                        body, idx = read_group(text, idx)
                        parts.append(render_segment(body))
                        continue

                    if cmd == "cdot":
                        parts.append("&middot;")
                        continue

                    if cmd == ",":
                        parts.append(" ")
                        continue

                    parts.append(self._escape_html("\\" + cmd))
                    continue

                if char in "_^":
                    tag = "sub" if char == "_" else "sup"
                    group, idx = read_group(text, idx + 1)
                    parts.append(f"<{tag}>{render_segment(group)}</{tag}>")
                    continue

                if char in "{}":
                    idx += 1
                    continue

                if char == "~":
                    parts.append("&nbsp;")
                    idx += 1
                    continue

                parts.append(self._escape_html(char))
                idx += 1

            return "".join(parts)

        return render_segment(str(latex).strip())

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
        lines.append(self._array_start("l"))
        lines.append(r"\textbf{" + section["title"] + r"}\\")
        colspec = self._array_colspec(len(kolumner))
        lines.append(self._array_start(colspec))

        max_rader = max(len(kolumn) for kolumn in kolumner)
        for radindex in range(max_rader):
            radceller = []
            for kolumn in kolumner:
                if radindex < len(kolumn):
                    item = kolumn[radindex]
                    lhs = self._format_lhs(item)
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
        lines.append(self._array_start("l"))
        lines.append(r"\textbf{" + section["title"] + r"}\\")
        colspec = self._array_colspec(len(kolumner))
        lines.append(self._array_start(colspec))

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

    def _build_method_block_html(self, section):
        """
        Bygger ett HTML-block för metodbeskrivning.

        Parametrar:
            section : dict
                Sektion med ``title`` och ``items`` där varje post innehåller
                ``rubrik`` och ``text``.

        Returvärde:
            str
                HTML-kod för metodbeskrivningen.
        """
        parts = [
            '<section class="anp-method-block">',
            f'<h3 class="anp-method-block__title">{self._escape_html(section["title"])}</h3>',
        ]

        for item in section["items"]:
            rubrik = self._escape_html(item.get("rubrik", ""))
            text = self._escape_html(item.get("text", ""))
            text = text.replace("\n", "<br>")
            parts.append('<div class="anp-method-block__item">')
            parts.append(f'<h4 class="anp-method-block__heading">{rubrik}</h4>')
            parts.append(f'<p class="anp-method-block__text">{text}</p>')
            parts.append("</div>")

        parts.append("</section>")
        return "\n".join(parts)

    def _build_section_block_html(self, section, etikett=False, decimals=None, rader=None):
        """
        Bygger ett HTML-block för en datasektion.

        Parametrar:
            section : dict
                Sektion med ``title`` och ``items``.

            etikett : bool, optional
                Om True visas etiketttext för varje post.

            decimals : dict[str, int] | None, optional
                Tillfällig override av antal decimaler.

            rader : int | None, optional
                Maximalt antal rader per intern kolumn.

        Returvärde:
            str
                HTML-kod för sektionen.
        """
        kolumner = self._dela_items_i_kolumner(section["items"], rader=rader)
        parts = [
            f'<section class="anp-data-block anp-data-block--cols-{len(kolumner)}">',
            f'<h3 class="anp-data-block__title">{self._escape_html(section["title"])}</h3>',
            f'<div class="anp-data-block__columns" style="--anp-cols: {len(kolumner)};">',
        ]

        for kolumn in kolumner:
            parts.append('<div class="anp-data-block__column">')
            for item in kolumn:
                lhs = self._latex_to_html(item["latex"])
                rhs = self._format_value_html(item, decimals_override=decimals)
                lhs_class = "anp-data-block__lhs"
                if isinstance(item.get("value"), (str, bool)):
                    lhs_class += " anp-data-block__lhs--text"
                parts.append('<div class="anp-data-block__row">')
                parts.append(f'<div class="{lhs_class}">{lhs}</div>')
                parts.append('<div class="anp-data-block__eq">=</div>')
                parts.append(f'<div class="anp-data-block__rhs">{rhs}</div>')
                if etikett and item.get("etikett"):
                    etikett_text = self._escape_html(item["etikett"])
                    parts.append(f'<div class="anp-data-block__etikett">{etikett_text}</div>')
                parts.append("</div>")
            parts.append("</div>")

        parts.append("</div>")
        parts.append("</section>")
        return "\n".join(parts)

    def _build_equation_block_html(self, section, etikett=False, rader=None):
        """
        Bygger ett HTML-block för en ekvationssektion.

        Parametrar:
            section : dict
                Sektion med ``title`` och ``items``.

            etikett : bool, optional
                Om True visas etiketttext för varje ekvation.

            rader : int | None, optional
                Maximalt antal rader per intern kolumn.

        Returvärde:
            str
                HTML-kod för sektionen.
        """
        kolumner = self._dela_items_i_kolumner(section["items"], rader=rader)
        parts = [
            f'<section class="anp-eq-block anp-eq-block--cols-{len(kolumner)}">',
            f'<h3 class="anp-eq-block__title">{self._escape_html(section["title"])}</h3>',
            f'<div class="anp-eq-block__columns" style="--anp-cols: {len(kolumner)};">',
        ]

        for kolumn in kolumner:
            parts.append('<div class="anp-eq-block__column">')
            for item in kolumn:
                uttryck = item["latex"]
                if "=" in uttryck:
                    vanster, hoger = uttryck.split("=", 1)
                else:
                    vanster, hoger = uttryck, ""

                vanster_html = self._latex_to_html(vanster.strip())
                hoger_html = self._latex_to_html(hoger.strip()) if hoger.strip() else ""

                parts.append('<div class="anp-eq-block__row">')
                parts.append(f'<div class="anp-eq-block__lhs">{vanster_html}</div>')
                parts.append('<div class="anp-eq-block__eq">=</div>')
                parts.append(f'<div class="anp-eq-block__rhs">{hoger_html}</div>')
                if etikett and item.get("etikett"):
                    etikett_text = self._escape_html(item["etikett"])
                    parts.append(f'<div class="anp-eq-block__etikett">{etikett_text}</div>')
                parts.append("</div>")
            parts.append("</div>")

        parts.append("</div>")
        parts.append("</section>")
        return "\n".join(parts)

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
        self.html_id = self._build_section_block_html(
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
        self.html_mb = self._build_method_block_html(self.details["metodbeskrivning"])
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
        self.html_dr = self._build_section_block_html(
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
        self.html_sr = self._build_section_block_html(
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
        self.html_ekv = self._build_equation_block_html(
            self.details["ekvationer"], etikett=etikett, rader=rader
        )
        self.latex = self.latex_ekv
        if visa:
            self._visa(self.latex_ekv)
