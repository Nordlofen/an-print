class Panel:
    """
    Notebookpanel for berakningsfunktioner med ett ``panel_schema``.

    Klassen ar en tunn orkestrerare: den bygger widgets fran schema, skapar
    ``px``, kor berakningsfunktionen och styr CalcBlock-redovisning.
    """

    DEFAULT_BLOCKS = {
        "MB": {"visa": False},
        "ID": {"visa": True, "etikett": True, "rader": 15},
        "DR": {"visa": True, "etikett": True, "rader": 30},
        "EKV": {"visa": False, "etikett": True, "rader": 15},
        "SR": {"visa": True, "etikett": True, "rader": 6},
    }
    BLOCK_LABELS = {
        "MB": "MB - Metodbeskrivning",
        "ID": "ID - Indata",
        "DR": "DR - Delresultat",
        "EKV": "EKV - Ekvationer",
        "SR": "SR - Slutresultat",
    }

    def __init__(self, funktion):
        schema = getattr(funktion, "panel_schema", None)
        if schema is None:
            namn = getattr(funktion, "__name__", repr(funktion))
            raise ValueError(f"{namn} saknar panel_schema.")

        self.funktion = funktion
        self.schema = schema
        self.px = None
        self.details = None
        self.cb = None

        self._widgets = self._load_widgets()
        self._field_widgets = {}
        self._table_widgets = {}
        self._block_widgets = {}
        self._style = {"description_width": "0px"}
        self._input_layout = self._widgets.Layout(width="180px")
        self._label_layout = self._widgets.Layout(width="255px")
        self._symbol_layout = self._widgets.Layout(width="50px")
        self._field_row_layout = self._widgets.Layout(width="535px", align_items="center")
        self.widget = self._build_widget()

    def _load_widgets(self):
        try:
            import ipywidgets as widgets
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "Panel kräver ipywidgets. Installera ipywidgets i notebookmiljön."
            ) from exc
        return widgets

    def _repr_mimebundle_(self, include=None, exclude=None):
        if hasattr(self.widget, "_repr_mimebundle_"):
            return self.widget._repr_mimebundle_(include=include, exclude=exclude)
        return None

    def _ipython_display_(self):
        try:
            from IPython.display import display
        except ModuleNotFoundError:
            return
        display(self.widget)

    def _build_widget(self):
        widgets = self._widgets
        title = self.schema.get("title") or getattr(self.funktion, "__name__", "Panel")
        children = [widgets.HTML(f"<h3>{title}</h3>")]
        children.append(self._build_fields_box())
        children.append(self._build_blocks_box())

        self._button = widgets.Button(description="Beräkna / uppdatera", button_style="primary")
        self._button.on_click(self._on_calculate_clicked)
        children.append(self._button)
        self._output = widgets.Output()
        children.append(self._output)
        return widgets.VBox(children)

    def _build_fields_box(self):
        widgets = self._widgets
        rows = []
        scalar_rows = []
        for field in self.schema.get("fields", []):
            if field.get("type") == "table":
                if scalar_rows:
                    rows.extend(self._two_column_rows(scalar_rows))
                    scalar_rows = []
                table = _TableInput(widgets, field)
                self._table_widgets[field["name"]] = table
                rows.append(table.widget)
            else:
                control = self._make_field_widget(field)
                self._field_widgets[field["name"]] = control
                scalar_rows.append(self._field_row(field, control))
        if scalar_rows:
            rows.extend(self._two_column_rows(scalar_rows))
        return widgets.VBox(rows)

    def _two_column_rows(self, field_rows):
        widgets = self._widgets
        rows = []
        for index in range(0, len(field_rows), 2):
            children = [field_rows[index]]
            if index + 1 < len(field_rows):
                children.append(field_rows[index + 1])
            rows.append(widgets.HBox(children, layout=widgets.Layout(gap="28px")))
        return rows

    def _field_row(self, field, control):
        widgets = self._widgets
        label = widgets.Label(self._field_label(field), layout=self._label_layout)
        symbol = widgets.HTML(self._field_symbol(field), layout=self._symbol_layout)
        return widgets.HBox([label, symbol, control], layout=self._field_row_layout)

    def _build_blocks_box(self):
        widgets = self._widgets
        rows = [widgets.HTML("<b>Redovisning</b>")]
        block_defaults = self.schema.get("blocks", {})
        for name in ("MB", "ID", "DR", "EKV", "SR"):
            defaults = dict(self.DEFAULT_BLOCKS[name])
            defaults.update(block_defaults.get(name, {}))

            visa = widgets.Checkbox(
                value=bool(defaults.get("visa", False)),
                description="",
                indent=False,
                layout=widgets.Layout(width="28px"),
            )
            block = {"visa": visa}
            controls = [
                widgets.Label(self.BLOCK_LABELS[name], layout=widgets.Layout(width="210px")),
                visa,
                widgets.Label("visa", layout=widgets.Layout(width="52px")),
            ]
            if name != "MB":
                etikett = widgets.Checkbox(
                    value=bool(defaults.get("etikett", True)),
                    description="",
                    indent=False,
                    layout=widgets.Layout(width="28px"),
                )
                rader = widgets.IntText(
                    value=int(defaults.get("rader", 10)),
                    description="",
                    layout=widgets.Layout(width="70px"),
                    style={"description_width": "0px"},
                )
                block.update({"etikett": etikett, "rader": rader})
                controls.extend(
                    [
                        etikett,
                        widgets.Label("etikett", layout=widgets.Layout(width="70px")),
                        widgets.Label("rader", layout=widgets.Layout(width="48px")),
                        rader,
                    ]
                )
            else:
                controls.extend(
                    [
                        widgets.Label("", layout=widgets.Layout(width="32px")),
                        widgets.Label("", layout=widgets.Layout(width="70px")),
                        widgets.Label("", layout=widgets.Layout(width="48px")),
                        widgets.Label("", layout=widgets.Layout(width="70px")),
                    ]
                )
            self._block_widgets[name] = block
            rows.append(widgets.HBox(controls, layout=widgets.Layout(gap="8px", align_items="center")))
        return widgets.VBox(rows, layout=widgets.Layout(width="650px"))

    def _field_label(self, field):
        unit = field.get("unit", "")
        label = field.get("label", field["name"])
        return f"{label} [{unit}]" if unit else label

    def _field_symbol(self, field):
        symbol = field.get("symbol") or field.get("latex") or field.get("name", "")
        return f"<span>{symbol}</span>"

    def _make_field_widget(self, field):
        widgets = self._widgets
        field_type = field.get("type", "float")
        default = field.get("default")
        description = ""
        if field_type == "float":
            return widgets.FloatText(
                value=float(default or 0.0),
                description=description,
                layout=self._input_layout,
                style=self._style,
            )
        if field_type == "int":
            return widgets.IntText(
                value=int(default or 0),
                description=description,
                layout=self._input_layout,
                style=self._style,
            )
        if field_type == "bool":
            return widgets.Checkbox(value=bool(default), description="")
        if field_type == "choice":
            options = [(option["label"], option["value"]) for option in field.get("options", [])]
            return widgets.Dropdown(
                options=options,
                value=default,
                description=description,
                layout=self._input_layout,
                style=self._style,
            )
        if field_type == "text":
            return widgets.Text(
                value="" if default is None else str(default),
                description=description,
                layout=self._input_layout,
                style=self._style,
            )
        raise ValueError(f"Okänd fälttyp: {field_type!r}.")

    def _on_calculate_clicked(self, _button):
        self._output.clear_output()
        with self._output:
            try:
                self.calculate()
            except Exception as exc:
                try:
                    from IPython.display import display

                    display(exc)
                except ModuleNotFoundError:
                    print(exc)

    def to_px(self):
        values = {}
        for name, widget in self._field_widgets.items():
            values[name] = widget.value
        for name, table in self._table_widgets.items():
            values.update(table.values())

        px = []
        for name in self.schema.get("px", []):
            if name not in values:
                raise ValueError(f"Saknar panelvärde för px-fältet {name!r}.")
            px.append(values[name])
        return px

    def calculate(self):
        from .calcblock import CalcBlock

        self.px = self.to_px()
        self.details = self.funktion(self.px)
        self.cb = CalcBlock(self.details)
        self._render_blocks()
        return self.details

    def _render_blocks(self):
        for name in ("MB", "ID", "DR", "EKV", "SR"):
            block = self._block_widgets[name]
            visa = bool(block["visa"].value)
            method = getattr(self.cb, name)
            if name == "MB":
                method(visa=visa)
            else:
                method(
                    visa=visa,
                    etikett=bool(block["etikett"].value),
                    rader=int(block["rader"].value),
                )


class _TableInput:
    def __init__(self, widgets, field):
        self.widgets = widgets
        self.field = field
        self._input_layout = widgets.Layout(width="120px")
        self._style = {"description_width": "0px"}
        self.rows_box = widgets.VBox([])
        self.rows = []
        self.widget = self._build_widget()
        defaults = field.get("default_rows") or [{}]
        for row in defaults:
            self.add_row(row)

    def _build_widget(self):
        widgets = self.widgets
        title = self.field.get("label", self.field["name"])
        add_button = widgets.Button(description="+ Lägg till rad", layout=widgets.Layout(width="150px"))
        add_button.on_click(lambda _button: self.add_row({}))
        header = self._header_row()
        return widgets.VBox(
            [widgets.HTML(f"<b>{title}</b>"), header, self.rows_box, add_button],
            layout=widgets.Layout(margin="10px 0 12px 0"),
        )

    def _header_row(self):
        widgets = self.widgets
        cells = [widgets.Label("", layout=widgets.Layout(width="34px"))]
        for column in self.field.get("columns", []):
            cells.append(widgets.HTML(self._column_header(column), layout=widgets.Layout(width="120px")))
        cells.append(widgets.Label("", layout=widgets.Layout(width="86px")))
        return widgets.HBox(cells, layout=widgets.Layout(gap="8px"))

    def add_row(self, values):
        widgets = self.widgets
        controls = {}
        for column in self.field.get("columns", []):
            default = values.get(column["name"], column.get("default", 0.0))
            control = self._make_column_widget(column, default)
            controls[column["name"]] = control

        remove_button = widgets.Button(description="Ta bort", layout=widgets.Layout(width="86px"))
        row = {"controls": controls, "widget": None}
        remove_button.on_click(lambda _button, row=row: self.remove_row(row))
        row["remove_button"] = remove_button
        row_widget = self._make_row_widget(row)
        row["widget"] = row_widget
        self.rows.append(row)
        self._refresh_rows()

    def _make_row_widget(self, row):
        widgets = self.widgets
        row_number = self.rows.index(row) + 1 if row in self.rows else len(self.rows) + 1
        cells = [widgets.Label(str(row_number), layout=widgets.Layout(width="34px"))]
        for column in self.field.get("columns", []):
            cells.append(row["controls"][column["name"]])
        cells.append(row["remove_button"])
        return widgets.HBox(cells, layout=widgets.Layout(gap="8px", align_items="center"))

    def remove_row(self, row):
        if row in self.rows:
            self.rows.remove(row)
            self._refresh_rows()

    def _refresh_rows(self):
        for row in self.rows:
            row["widget"] = self._make_row_widget(row)
        self.rows_box.children = [row["widget"] for row in self.rows]

    def _column_label(self, column):
        unit = column.get("unit", "")
        label = column.get("label", column["name"])
        return f"{label} [{unit}]" if unit else label

    def _column_header(self, column):
        symbol = column.get("symbol") or column.get("latex") or column.get("name", "")
        label = self._column_label(column)
        return f"<span>{symbol}</span><br><span>{label}</span>"

    def _make_column_widget(self, column, default):
        widgets = self.widgets
        column_type = column.get("type", "float")
        if column_type == "float":
            return widgets.FloatText(
                value=float(default or 0.0),
                description="",
                layout=self._input_layout,
                style=self._style,
            )
        if column_type == "int":
            return widgets.IntText(
                value=int(default or 0),
                description="",
                layout=self._input_layout,
                style=self._style,
            )
        if column_type == "text":
            return widgets.Text(
                value="" if default is None else str(default),
                description="",
                layout=self._input_layout,
                style=self._style,
            )
        if column_type == "choice":
            options = [(option["label"], option["value"]) for option in column.get("options", [])]
            return widgets.Dropdown(
                options=options,
                value=default,
                description="",
                layout=self._input_layout,
                style=self._style,
            )
        if column_type == "bool":
            return widgets.Checkbox(value=bool(default), description="")
        raise ValueError(f"Okänd tabellkolumntyp: {column_type!r}.")

    def values(self):
        result = {}
        for output_name in self.field.get("outputs", []):
            result[output_name] = []

        for row in self.rows:
            for column in self.field.get("columns", []):
                output = column.get("output", column["name"])
                if output in result:
                    result[output].append(row["controls"][column["name"]].value)
        return result
