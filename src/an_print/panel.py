import html
import json
from pathlib import Path


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
    _LAST_VALUES = {}
    STATE_FILENAME = ".an_print_panel_state.json"

    def __init__(self, funktion, use_last=True, persist=True):
        schema = getattr(funktion, "panel_schema", None)
        if schema is None:
            namn = getattr(funktion, "__name__", repr(funktion))
            raise ValueError(f"{namn} saknar panel_schema.")

        self.funktion = funktion
        self.schema = schema
        self.use_last = use_last
        self.persist = persist
        self.px = None
        self.details = None
        self.cb = None
        self._last_key = self._make_last_key(funktion)
        self._initial_values = self._load_initial_values() if use_last else {}

        self._widgets = self._load_widgets()
        self._field_widgets = {}
        self._field_rows = {}
        self._scalar_field_groups = []
        self._table_widgets = {}
        self._block_widgets = {}
        self._style = {"description_width": "0px"}
        self._input_layout = self._widgets.Layout(width="70px")
        self._label_layout = self._widgets.Layout(width="325px")
        self._symbol_layout = self._widgets.Layout(width="80px")
        self.widget = self._build_widget()
        self._attach_autosave_observers()

    def _make_last_key(self, funktion):
        module = getattr(funktion, "__module__", "")
        name = getattr(funktion, "__name__", repr(funktion))
        return f"{module}.{name}"

    def _state_path(self):
        return Path.cwd() / self.STATE_FILENAME

    def _load_initial_values(self):
        values = {}
        if self.persist:
            values.update(self._read_persisted_values().get(self._last_key, {}))
        values.update(self._LAST_VALUES.get(self._last_key, {}))
        return values

    def _read_persisted_values(self):
        path = self._state_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_persisted_values(self):
        if not self.persist:
            return
        state = self._read_persisted_values()
        state[self._last_key] = self._LAST_VALUES.get(self._last_key, {})
        self._state_path().write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

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
        scalar_fields = []
        for field in self.schema.get("fields", []):
            if field.get("type") == "table":
                if scalar_fields:
                    self._add_scalar_field_group(rows, scalar_fields)
                    scalar_fields = []
                table = _TableInput(
                    widgets,
                    field,
                    self._initial_values.get(field["name"]),
                    on_change=self._save_last_values,
                )
                self._table_widgets[field["name"]] = table
                rows.append(table.widget)
            else:
                control = self._make_field_widget(field)
                self._field_widgets[field["name"]] = control
                field_row = self._field_row(field, control)
                self._field_rows[field["name"]] = field_row
                scalar_fields.append(field)
        if scalar_fields:
            self._add_scalar_field_group(rows, scalar_fields)
        fields_box = widgets.VBox(rows)
        self._setup_visibility_rules()
        self._refresh_field_groups()
        return fields_box

    def _add_scalar_field_group(self, rows, fields):
        group_box = self._widgets.VBox([])
        self._scalar_field_groups.append({"box": group_box, "fields": list(fields)})
        rows.append(group_box)

    def _two_column_rows(self, field_rows):
        widgets = self._widgets
        rows = []
        split_index = (len(field_rows) + 1) // 2
        left_rows = field_rows[:split_index]
        right_rows = field_rows[split_index:]
        for index, left_row in enumerate(left_rows):
            children = [left_row]
            if index < len(right_rows):
                children.append(right_rows[index])
            rows.append(widgets.HBox(children, layout=widgets.Layout(gap="28px")))
        return rows

    def _field_row(self, field, control):
        widgets = self._widgets
        label = widgets.HTML(self._field_label_html(field), layout=self._label_layout)
        symbol = widgets.HTML(self._field_symbol(field), layout=self._symbol_layout)
        row_layout = widgets.Layout(width="500px", align_items="center")
        return widgets.HBox([label, symbol, control], layout=row_layout)

    def _setup_visibility_rules(self):
        for field in self.schema.get("fields", []):
            visible_if = field.get("visible_if")
            if not visible_if:
                continue
            controller_name = visible_if.get("field")
            controller = self._field_widgets.get(controller_name)
            if controller is None:
                continue
            if hasattr(controller, "observe"):
                controller.observe(lambda _change: self._refresh_field_groups(), names="value")

    def _refresh_field_groups(self):
        for group in self._scalar_field_groups:
            visible_rows = [
                self._field_rows[field["name"]]
                for field in group["fields"]
                if self._field_is_visible(field)
            ]
            group["box"].children = self._two_column_rows(visible_rows)

    def _field_is_visible(self, field):
        visible_if = field.get("visible_if")
        if not visible_if:
            return True
        controller = self._field_widgets.get(visible_if.get("field"))
        if controller is None:
            return True
        return self._visible_if_matches(controller.value, visible_if)

    def _visible_if_matches(self, value, visible_if):
        if "equals" in visible_if:
            return value == visible_if["equals"]
        if "not_equals" in visible_if:
            return value != visible_if["not_equals"]
        if "in" in visible_if:
            return value in visible_if["in"]
        if "not_in" in visible_if:
            return value not in visible_if["not_in"]
        return True

    def _build_blocks_box(self):
        widgets = self._widgets
        rows = [widgets.HTML("<b>Redovisning</b>")]
        block_defaults = self.schema.get("blocks", {})
        saved_blocks = self._initial_values.get("__blocks__", {})
        for name in ("MB", "ID", "DR", "EKV", "SR"):
            defaults = dict(self.DEFAULT_BLOCKS[name])
            defaults.update(block_defaults.get(name, {}))
            defaults.update(saved_blocks.get(name, {}))

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

    def _field_label_html(self, field):
        label = html.escape(self._field_label(field))
        return (
            "<div style='white-space: normal; overflow: visible; "
            "line-height: 1.25; padding-right: 8px;'>"
            f"{label}</div>"
        )

    def _field_symbol(self, field):
        if "symbol" in field:
            symbol = field["symbol"]
        else:
            symbol = field.get("latex") or field.get("name", "")
        return f"<span style='display: inline-block; padding-left: 8px;'>{symbol}</span>"

    def _make_field_widget(self, field):
        widgets = self._widgets
        field_type = field.get("type", "float")
        default = self._initial_values.get(field["name"], field.get("default"))
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
            return widgets.Checkbox(
                value=bool(default),
                description="",
                indent=False,
                layout=self._input_layout,
            )
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

    def _attach_autosave_observers(self):
        for widget in self._field_widgets.values():
            if hasattr(widget, "observe"):
                widget.observe(lambda _change: self._save_last_values(), names="value")
        for block in self._block_widgets.values():
            for widget in block.values():
                if hasattr(widget, "observe"):
                    widget.observe(lambda _change: self._save_last_values(), names="value")
        self._save_last_values()

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
        self._save_last_values()
        self._render_blocks()
        return self.details

    def _save_last_values(self):
        values = {}
        for name, widget in self._field_widgets.items():
            values[name] = widget.value
        for name, table in self._table_widgets.items():
            values[name] = table.rows_as_values()
        values["__blocks__"] = self._block_values()
        self._LAST_VALUES[self._last_key] = values
        self._write_persisted_values()

    def _block_values(self):
        values = {}
        for name, block in self._block_widgets.items():
            block_values = {"visa": bool(block["visa"].value)}
            if name != "MB":
                block_values["etikett"] = bool(block["etikett"].value)
                block_values["rader"] = int(block["rader"].value)
            values[name] = block_values
        return values

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
    def __init__(self, widgets, field, initial_rows=None, on_change=None):
        self.widgets = widgets
        self.field = field
        self.on_change = on_change
        self._input_layout = widgets.Layout(width="120px")
        self._style = {"description_width": "0px"}
        self.rows_box = widgets.VBox([])
        self.rows = []
        self.widget = self._build_widget()
        defaults = initial_rows or field.get("default_rows") or [{}]
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
            if hasattr(control, "observe"):
                control.observe(lambda _change: self._notify_change(), names="value")
            controls[column["name"]] = control

        remove_button = widgets.Button(description="Ta bort", layout=widgets.Layout(width="86px"))
        row = {"controls": controls, "widget": None}
        remove_button.on_click(lambda _button, row=row: self.remove_row(row))
        row["remove_button"] = remove_button
        row_widget = self._make_row_widget(row)
        row["widget"] = row_widget
        self.rows.append(row)
        self._refresh_rows()
        self._notify_change()

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
            self._notify_change()

    def _notify_change(self):
        if self.on_change is not None:
            self.on_change()

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

    def rows_as_values(self):
        values = []
        for row in self.rows:
            row_values = {}
            for column in self.field.get("columns", []):
                row_values[column["name"]] = row["controls"][column["name"]].value
            values.append(row_values)
        return values
