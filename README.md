# an-print

Presentationsrepo for byggda resultatblock och layout.

## Kontrakt

`an_print` arbetar mot standardiserade `details`-dictionarys fran
`an_calcs`.

Det klassiska arbetsflodet ar oforandrat:

```python
details = funktion(px)

cb = CalcBlock(details)
cb.ID(visa=True, etikett=True, rader=15)
cb.DR(visa=True, etikett=True, rader=30)
cb.SR(visa=True, etikett=True, rader=6)
```

`CalcBlock` ansvarar for redovisningsblock:

- `MB` - metodbeskrivning
- `ID` - indata
- `DR` - delresultat
- `EKV` - ekvationer
- `SR` - slutresultat

`CalcLayout` ansvarar for att arrangera redan byggda block fran ett eller flera
`CalcBlock`-objekt.

En numerisk datapost kan ange `"format": "scientific"` och `"decimals": 2`
för tiopotensform med två decimaler i mantissan, exempelvis
`8.20 · 10^4`. Det gäller både LaTeX och HTML; `value` behåller full precision.
`decimals` kan även överstyras per post vid anrop av redovisningsblocket.

## Panel

`Panel` ar ett frivilligt notebooklager ovanpa samma kontrakt. Den ersatter
inte `CalcBlock`, utan skapar `px`, kor berakningen och styr `CalcBlock`.

Exempel:

```python
from an_calcs.geo import allmanna_barighetsekvationen
from an_print import Panel

panel = Panel(allmanna_barighetsekvationen)
panel
```

Rekommenderat for notebooks med flera paneler ar att valja state-fil hogst upp
i notebooken:

```python
from an_print import Panel

Panel.configure_state_file("26022_smalandsvillan.panel_state.json")
```

`Panel` har ett öppningsbart avsnitt **Beräkningsfall**, där fall kan väljas,
skapas, bytas namn på och tas bort. Skriv ett fallnamn i fältet **Namn** och
klicka `Spara` for att skriva aktuella indata och redovisningsval till
state-filen. `Berakna / uppdatera` kor bara berakningen och renderar
redovisningen. For namngivna fall kan `Kopiera Key` anvandas for att kopiera
ett Python-argument som `key="fall_1"` till urklipp.

Sparade varden ateranvands i nya paneler och skrivs till den konfigurerade
state-filen, eller defaultfilen `.an_print_panel_state.json` i aktuell
arbetsmapp, sa de finns kvar efter restart av kernel nar cellen kors igen.

```python
panel = Panel(allmanna_barighetsekvationen)                  # anvand senaste varden
panel = Panel(allmanna_barighetsekvationen, key="fall_1")     # separat state per fall
panel = Panel(allmanna_barighetsekvationen, state_file="annan.json")
```

Nar en panel skapas laddas startvarden i denna ordning:

1. sparade varden for exakt samma funktion och `key`, om `key` anges
2. senaste sparade panel for samma funktion i samma state-fil
3. defaultvarden fran `panel_schema`

Det betyder att ett nytt fall kan borja som kopia av foregaende panel for samma
funktion, men sparas separat nar anvandaren skriver ett nytt fallnamn och
klickar `Spara`.

Vid knapptryck:

```python
panel.px       # senast byggda px-lista
panel.details  # senast beraknade details
panel.cb       # senast skapade CalcBlock
```

For att en funktion ska fungera med `Panel` maste den ha ett
`panel_schema`-attribut. Schemat ligger pa berakningsfunktionen i `an_calcs`
och ska vara ren Python-data utan widgetimporter.

`Panel` stoder falttyperna:

- `float`
- `int`
- `text`
- `bool`
- `choice`
- `table`

Ett skalärt fält kan ha `fixed_if` för att visa ett låst värde när ett
villkor gäller. Exempel: `{"field": "typ", "equals": "VS", "value": 1.0}`.
Fältet ligger kvar synligt och återfår sitt tidigare redigerbara värde när
villkoret upphör. Båda värdena följer med sparade beräkningsfall.
`presentation_if` använder samma villkor och kan ändra `label`, `unit`
och `symbol`, exempelvis från kraft i kN till linjelast i kN/m.
Villkoren stöder samma `equals`, `not_equals`, `in`, `not_in` och `all`
som `visible_if`.

Alla paneler använder samma formgivning med etiketter över fälten, anpassningsbara
kolumnbredder och en separat, fullbred yta för beräkningsresultaten. Befintliga
`Panel(funktion, key=...)`-anrop och sparade JSON-fall fungerar som tidigare.
**Beräkningsfall** och **Redovisning** är stängda från början och öppnas via rubriken.

För anpassad gruppering kan schemat ange `sections`. Varje avsnitt kan ha
`title`, `fields` (fältnamn i visningsordning), `columns` (1–3),
`collapsible`, `collapsed` och en kort `summary` eller `summary_fields`.
Underavsnitt anges med en inre `sections`-lista, exempelvis för Del 1 och Del 2
sida vid sida. `px` bestämmer alltid ordningen för beräkningsindata, oberoende
av fältens visuella placering. Fält som saknas i avsnitten visas sist;
okända eller upprepade fältnamn avvisas.

```python
funktion.panel_schema["sections"] = [
    {"title": "Geometri", "fields": ["bx", "by"], "columns": 2},
    {"title": "Inställningar", "fields": ["t_skikt"],
     "collapsible": True, "collapsed": True},
]
```

Ett fält kan ange `span: 2` för större bredd och `display_label` för en kortare
synlig etikett inom en namngiven grupp. Den fullständiga `label` används fortsatt
för tillgänglighetsnamnet. Tabeller kan ange `add_label` för knappen som lägger
till en rad. Den sista tabellraden behålls alltid.

Avsnitt och fält följer `visible_if` även efter fallbyte. Att stänga ett avsnitt
behåller dess värden. Stilen är avgränsad till panelen och följer JupyterLabs
ljusa eller mörka tema. Inga nya notebooktillägg behöver installeras.

Fält med `group` samlas efter de vanliga fälten i ett utfällbart avsnitt.
Gruppens namn blir rubrik. `panel_schema["groups"]` kan ange exempelvis
`{"Beräkningsinställningar": {"collapsed": True}}`. Gruppfälten finns
alltid med i `px`, även när avsnittet är stängt.

Redovisningsdelen i `Panel` ar blockspecifik och motsvarar anropen till
`CalcBlock.MB`, `CalcBlock.ID`, `CalcBlock.DR`, `CalcBlock.EKV` och
`CalcBlock.SR`.

Foreslagen struktur:

- `src/an_print` for block, layout, panel och senare exportfunktioner
- `tests/` for tester
- `notebooks/` for exempel och visuella prototyper
- `docs/` for dokumentation
