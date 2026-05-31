import html
import json
from pathlib import Path


class Panel:
    """
    Notebookpanel for berakningsfunktioner med ett ``panel_schema``.

    Klassen ar en tunn orkestrerare: den bygger widgets fran schema, skapar
    ``px``, kor berakningsfunktionen och styr CalcBlock-redovisning.

    Grundanvandning i notebook:

    ```python
    from an_calcs.geo import allmanna_barighetsekvationen
    from an_print import Panel

    panel = Panel(allmanna_barighetsekvationen)
    panel
    ```

    Om samma notebook innehaller flera paneler for samma berakningsfunktion
    ska ``key`` anvandas for att spara separata indata:

    ```python
    Panel(allmanna_barighetsekvationen, key="krysskran_10x10_barighet")
    Panel(allmanna_barighetsekvationen, key="krysskran_6x6_barighet")
    ```

    Nar en panel skapas laddas startvarden i denna ordning:

    1. sparade varden for exakt samma funktion och ``key``
    2. senaste sparade panel for samma funktion i samma state-fil
    3. defaultvarden fran ``panel_schema``

    Det gor att ett nytt berakningsfall kan starta som kopia av foregaende
    panel for samma funktion, men far egen state nar anvandaren sparar.

    Panelen visar en fallrad med en combobox och knapparna ``Spara``,
    ``Byt namn`` och ``Ta bort``. Skriv ett nytt fallnamn och klicka
    ``Spara`` for att skapa ett nytt sparat fall fran aktuella indata.
    Valj ett befintligt fall i comboboxen for att ladda det. ``Byt namn``
    flyttar aktivt fall till det namn som star i comboboxen.

    Faltvarden sparas i en JSON-fil nar anvandaren klickar ``Spara``.
    ``Berakna / uppdatera`` kor berakningen och renderar redovisning utan att
    skriva panelstate. Default ar ``.an_print_panel_state.json`` i
    aktuell arbetsmapp. For en notebook eller ett projekt kan en egen
    state-fil valjas en gang hogst upp:

    ```python
    Panel.configure_state_file("26022_smalandsvillan.panel_state.json")
    ```

    Prioritet for state-fil ar:

    1. ``state_file`` direkt i ``Panel(...)``
    2. fil satt via ``Panel.configure_state_file(...)``
    3. default ``.an_print_panel_state.json``

    Parametrar:
        funktion:
            Berakningsfunktion med ett ``panel_schema``-attribut.

        key:
            Frivillig nyckel for att skilja flera paneler for samma funktion.
            Utan key delar alla paneler for samma funktion sparade varden.

        state_file:
            Frivillig filvag for just denna panel. Gar fore global
            ``configure_state_file``.
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
    _LAST_BY_FUNCTION = {}
    STATE_FILENAME = ".an_print_panel_state.json"
    STATE_META_KEY = "__an_print_panel_meta__"
    _STATE_FILE = None

    def __init__(self, funktion, key=None, state_file=None):
        schema = getattr(funktion, "panel_schema", None)
        if schema is None:
            namn = getattr(funktion, "__name__", repr(funktion))
            raise ValueError(f"{namn} saknar panel_schema.")

        self.funktion = funktion
        self.schema = schema
        self.key = key
        self.state_file = state_file
        self.px = None
        self.details = None
        self.cb = None
        self._base_key = self._make_base_key(funktion)
        self._case_key = "" if key is None else str(key)
        self._last_key = self._initial_state_key(key)
        self._initial_values = self._load_initial_values()
        self._suspend_case_observer = False

        self._widgets = self._load_widgets()
        self._field_widgets = {}
        self._field_rows = {}
        self._scalar_field_groups = []
        self._table_widgets = {}
        self._block_widgets = {}
        self._case_combo = None
        self._case_name_input = None
        self._case_save_button = None
        self._case_rename_button = None
        self._case_delete_button = None
        self._case_reset_button = None
        self._case_copy_key_html = None
        self._case_status = None
        self._style = {"description_width": "0px"}
        self._input_layout = self._widgets.Layout(width="70px")
        self._label_layout = self._widgets.Layout(width="210px")
        self._symbol_layout = self._widgets.Layout(width="70px")
        self.widget = self._build_widget()
        self._attach_autosave_observers()

    @classmethod
    def configure_state_file(cls, state_file):
        """
        Valjer defaultfil for panelstate i aktuell Python-session.

        Anropas typiskt en gang hogst upp i en notebook:

        ```python
        from an_print import Panel

        Panel.configure_state_file("26022_smalandsvillan.panel_state.json")
        ```

        Alla efterfoljande ``Panel(...)`` utan eget ``state_file`` anvander
        denna fil. Relativa sokvagar tolkas relativt ``Path.cwd()``.

        Om flera notebooks delar samma kernel galler senast anropad
        ``configure_state_file`` for den kernel-sessionen.
        """
        cls._STATE_FILE = state_file

    def _make_base_key(self, funktion):
        module = getattr(funktion, "__module__", "")
        name = getattr(funktion, "__name__", repr(funktion))
        return f"{module}.{name}"

    def _make_last_key(self, funktion, key=None):
        base = self._make_base_key(funktion)
        if key is None:
            return base
        return f"{base}:{key}"

    def _initial_state_key(self, key):
        if key is not None:
            return self._make_last_key(self.funktion, key)
        return self._base_key

    def _state_path(self):
        state_file = self.state_file or self._STATE_FILE or self.STATE_FILENAME
        path = Path(state_file)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def _load_initial_values(self):
        values = self._load_values_for_key(self._last_key)
        if not values:
            fallback_key = self._last_key_for_function()
            if fallback_key and fallback_key != self._last_key:
                values = self._load_values_for_key(fallback_key)
        return values

    def _load_values_for_key(self, key):
        values = {}
        values.update(self._read_persisted_values().get(key, {}))
        values.update(self._LAST_VALUES.get(key, {}))
        return values

    def _last_key_for_function(self):
        if self._base_key in self._LAST_BY_FUNCTION:
            return self._LAST_BY_FUNCTION[self._base_key]
        state = self._read_persisted_values()
        return state.get(self.STATE_META_KEY, {}).get("last_by_function", {}).get(self._base_key)

    def _read_persisted_values(self):
        path = self._state_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_persisted_values(self):
        self._write_values_for_key(self._last_key, self._LAST_VALUES.get(self._last_key, {}))

    def _write_values_for_key(self, key, values):
        state = self._read_persisted_values()
        state[key] = values
        meta = state.setdefault(self.STATE_META_KEY, {})
        last_by_function = meta.setdefault("last_by_function", {})
        last_by_function[self._base_key] = key
        self._state_path().write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _write_state(self, state):
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
        children.append(self._build_case_box())
        children.append(self._build_fields_box())
        children.append(self._build_blocks_box())

        self._button = widgets.Button(description="Beräkna / uppdatera", button_style="primary")
        self._button.on_click(self._on_calculate_clicked)
        children.append(self._button)
        self._output = widgets.Output()
        children.append(self._output)
        return widgets.VBox(children)

    def _build_case_box(self):
        widgets = self._widgets
        self._case_combo = widgets.Dropdown(
            value=self._case_display_from_state_key(self._last_key),
            options=self._case_options(),
            description="Fall",
            layout=widgets.Layout(width="230px"),
        )
        self._case_combo.observe(self._on_case_changed, names="value")

        self._case_name_input = widgets.Text(
            value="",
            description="",
            layout=widgets.Layout(width="230px"),
            style={"description_width": "0px"},
        )
        self._case_name_input.observe(self._on_case_name_changed, names="value")

        self._case_save_button = widgets.Button(description="Spara")
        self._case_save_button.on_click(self._on_case_save_clicked)
        self._case_rename_button = widgets.Button(description="Byt namn")
        self._case_rename_button.on_click(self._on_case_rename_clicked)
        self._case_delete_button = widgets.Button(description="Ta bort")
        self._case_delete_button.on_click(self._on_case_delete_clicked)
        self._case_reset_button = widgets.Button(description="Återställ")
        self._case_reset_button.on_click(self._on_case_reset_clicked)
        self._case_copy_key_html = widgets.HTML("")
        self._case_status = widgets.HTML("")

        controls = widgets.HBox(
            [
                self._case_combo,
                self._case_name_input,
                self._case_save_button,
                self._case_rename_button,
                self._case_delete_button,
                self._case_reset_button,
                self._case_copy_key_html,
                self._case_status,
            ],
            layout=widgets.Layout(gap="8px", align_items="center", margin="0 0 10px 0"),
        )
        self._refresh_case_controls()
        return controls

    def _case_key_from_state_key(self, state_key):
        prefix = f"{self._base_key}:"
        if state_key.startswith(prefix):
            return state_key[len(prefix):]
        return ""

    def _case_display(self, case_key):
        return "-" if not case_key else case_key

    def _display_to_case_key(self, display_value):
        case_key = "" if display_value is None else str(display_value).strip()
        if case_key == "-":
            return ""
        return case_key

    def _case_display_from_state_key(self, state_key):
        return self._case_display(self._case_key_from_state_key(state_key))

    def _state_key_for_case(self, case_key):
        case_key = self._display_to_case_key(case_key)
        if not case_key:
            return self._base_key
        return f"{self._base_key}:{case_key}"

    def _case_options(self):
        keys = set()
        state = self._read_persisted_values()
        prefix = f"{self._base_key}:"
        keys.add("")
        for source in (state, self._LAST_VALUES):
            for key in source:
                if key == self._base_key:
                    keys.add("")
                elif key.startswith(prefix):
                    keys.add(key[len(prefix):])
        named_keys = sorted(key for key in keys if key)
        return [self._case_display("")] + named_keys

    def _refresh_case_options(self):
        if self._case_combo is None:
            return
        self._case_combo.options = self._case_options()

    def _set_case_status(self, message):
        if self._case_status is not None:
            self._case_status.value = (
                "<span style='color:#555; font-size:12px;'>" + html.escape(message) + "</span>"
            )

    def _refresh_case_controls(self):
        active_is_base = not self._case_key
        name_value = "" if self._case_name_input is None else str(self._case_name_input.value).strip()
        if self._case_save_button is not None:
            self._case_save_button.disabled = active_is_base and not name_value
        if self._case_rename_button is not None:
            self._case_rename_button.disabled = active_is_base or not name_value
        if self._case_delete_button is not None:
            self._case_delete_button.disabled = active_is_base
        if self._case_reset_button is not None:
            self._case_reset_button.disabled = active_is_base
        self._refresh_copy_key_button()

    def _refresh_copy_key_button(self):
        if self._case_copy_key_html is None:
            return
        style = (
            "font: inherit; padding: 3px 8px; border: 1px solid #ccc; "
            "border-radius: 2px; background: #f7f7f7;"
        )
        if not self._case_key:
            self._case_copy_key_html.value = (
                f"<button type='button' disabled style='{style} color: #999;'>"
                "Kopiera Key</button>"
            )
            return

        snippet = f'key="{self._case_key}"'
        js = (
            f"navigator.clipboard.writeText({json.dumps(snippet, ensure_ascii=False)})"
            ".then(() => { this.textContent = 'Kopierat'; })"
            ".catch(() => { this.textContent = 'Kunde inte kopiera'; });"
        )
        self._case_copy_key_html.value = (
            f"<button type='button' style='{style}' onclick=\"{html.escape(js, quote=True)}\">"
            "Kopiera Key</button>"
        )

    def _on_case_changed(self, change):
        if self._suspend_case_observer:
            return
        case_key = self._display_to_case_key(change.get("new"))
        state_key = self._state_key_for_case(case_key)
        values = self._load_values_for_key(state_key)
        self._set_active_state_key(state_key)
        if self._case_name_input is not None:
            self._case_name_input.value = ""
        self._refresh_case_controls()
        if values:
            self._apply_values(values)
            self._set_case_status("Laddat")

    def _on_case_name_changed(self, _change):
        self._refresh_case_controls()

    def _on_case_save_clicked(self, _button):
        case_key = ""
        if self._case_name_input is not None and str(self._case_name_input.value).strip():
            case_key = str(self._case_name_input.value).strip()
        elif self._case_combo is not None:
            case_key = self._display_to_case_key(self._case_combo.value)
        else:
            case_key = self._case_key
        self._save_case(case_key)

    def _on_case_rename_clicked(self, _button):
        new_case_key = "" if self._case_name_input is None else str(self._case_name_input.value).strip()
        self._rename_case(new_case_key)

    def _on_case_delete_clicked(self, _button):
        self._delete_active_case()

    def _on_case_reset_clicked(self, _button):
        self._reset_active_case()

    def _set_active_state_key(self, state_key):
        self._last_key = state_key
        self._case_key = self._case_key_from_state_key(state_key)
        self.key = self._case_key or None
        if self._case_combo is not None:
            self._suspend_case_observer = True
            try:
                display = self._case_display(self._case_key)
                if display not in list(self._case_combo.options):
                    self._case_combo.options = self._case_options()
                if display not in list(self._case_combo.options):
                    self._case_combo.options = list(self._case_combo.options) + [display]
                self._case_combo.value = display
            finally:
                self._suspend_case_observer = False
        self._refresh_case_controls()

    def _save_case(self, case_key):
        state_key = self._state_key_for_case(case_key)
        self._set_active_state_key(state_key)
        self._save_last_values()
        self._refresh_case_options()
        if self._case_name_input is not None:
            self._case_name_input.value = ""
        self._set_case_status("Sparat")

    def _rename_case(self, new_case_key):
        new_case_key = self._display_to_case_key(new_case_key)
        new_state_key = self._state_key_for_case(new_case_key)
        if new_state_key == self._last_key:
            self._set_case_status("Oförändrat namn")
            return
        values = self._collect_values()
        state = self._read_persisted_values()
        state.pop(self._last_key, None)
        state[new_state_key] = values
        meta = state.setdefault(self.STATE_META_KEY, {})
        meta.setdefault("last_by_function", {})[self._base_key] = new_state_key
        self._write_state(state)

        self._LAST_VALUES.pop(self._last_key, None)
        self._LAST_VALUES[new_state_key] = values
        self._LAST_BY_FUNCTION[self._base_key] = new_state_key
        self._set_active_state_key(new_state_key)
        self._refresh_case_options()
        if self._case_name_input is not None:
            self._case_name_input.value = ""
        self._set_case_status("Bytte namn")

    def _reset_active_case(self):
        values = self._load_values_for_key(self._last_key)
        if not values:
            return
        self._apply_values(values)
        if self._case_name_input is not None:
            self._case_name_input.value = ""
        self._set_case_status("Återställd")

    def _delete_active_case(self):
        state = self._read_persisted_values()
        state.pop(self._last_key, None)
        self._LAST_VALUES.pop(self._last_key, None)

        next_key = self._next_state_key_after_delete(state)
        meta = state.setdefault(self.STATE_META_KEY, {})
        last_by_function = meta.setdefault("last_by_function", {})
        if next_key:
            last_by_function[self._base_key] = next_key
        else:
            last_by_function.pop(self._base_key, None)
        self._write_state(state)

        if next_key:
            self._set_active_state_key(next_key)
            self._apply_values(self._load_values_for_key(next_key))
        else:
            self._set_active_state_key(self._base_key)
            self._apply_values({})
        self._LAST_BY_FUNCTION.pop(self._base_key, None)
        if next_key:
            self._LAST_BY_FUNCTION[self._base_key] = next_key
        self._refresh_case_options()
        if self._case_name_input is not None:
            self._case_name_input.value = ""
        self._refresh_case_controls()
        self._set_case_status("Tog bort")

    def _next_state_key_after_delete(self, state):
        keys = self._state_keys_for_function(state)
        if not keys:
            return None
        previous_latest = state.get(self.STATE_META_KEY, {}).get("last_by_function", {}).get(self._base_key)
        if previous_latest in keys:
            return previous_latest
        return keys[-1]

    def _state_keys_for_function(self, state):
        prefix = f"{self._base_key}:"
        keys = []
        if self._base_key in state:
            keys.append(self._base_key)
        keys.extend(key for key in state if key.startswith(prefix))
        return keys

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
                    on_change=self._mark_dirty,
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
                children.append(widgets.HTML("", layout=widgets.Layout(width="80px")))
                children.append(right_rows[index])
            rows.append(widgets.HBox(children))
        return rows

    def _field_row(self, field, control):
        widgets = self._widgets
        label = widgets.HTML(self._field_label_html(field), layout=self._label_layout)
        symbol = widgets.HTML(self._field_symbol(field), layout=self._symbol_layout)
        row_layout = widgets.Layout(width="380px", align_items="center")
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
                widget.observe(lambda _change: self._mark_dirty(), names="value")
        if self._case_name_input is not None and hasattr(self._case_name_input, "observe"):
            self._case_name_input.observe(lambda _change: self._refresh_case_controls(), names="value")
        for block in self._block_widgets.values():
            for widget in block.values():
                if hasattr(widget, "observe"):
                    widget.observe(lambda _change: self._mark_dirty(), names="value")

    def _mark_dirty(self):
        self._set_case_status("Osparat")

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

    def _save_last_values(self):
        values = self._collect_values()
        self._LAST_VALUES[self._last_key] = values
        self._LAST_BY_FUNCTION[self._base_key] = self._last_key
        self._write_persisted_values()
        self._refresh_case_options()
        self._set_case_status("Sparat")

    def _collect_values(self):
        values = {}
        for name, widget in self._field_widgets.items():
            values[name] = widget.value
        for name, table in self._table_widgets.items():
            values[name] = table.rows_as_values()
        values["__blocks__"] = self._block_values()
        return values

    def _apply_values(self, values):
        self._suspend_case_observer = True
        try:
            for field in self.schema.get("fields", []):
                name = field["name"]
                if field.get("type") == "table":
                    table = self._table_widgets.get(name)
                    if table is not None:
                        table.set_rows(values.get(name, field.get("default_rows") or [{}]))
                    continue
                widget = self._field_widgets.get(name)
                if widget is not None:
                    widget.value = values.get(name, field.get("default"))
            saved_blocks = values.get("__blocks__", {})
            for name, block in self._block_widgets.items():
                defaults = dict(self.DEFAULT_BLOCKS[name])
                defaults.update(self.schema.get("blocks", {}).get(name, {}))
                defaults.update(saved_blocks.get(name, {}))
                block["visa"].value = bool(defaults.get("visa", False))
                if name != "MB":
                    block["etikett"].value = bool(defaults.get("etikett", True))
                    block["rader"].value = int(defaults.get("rader", 10))
            self._refresh_field_groups()
        finally:
            self._suspend_case_observer = False
        self._refresh_case_controls()

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

    def set_rows(self, rows):
        self.rows = []
        self.rows_box.children = []
        for row in rows or [{}]:
            self.add_row(row)

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
