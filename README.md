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

`Panel` sparar faltandringar automatiskt per berakningsfunktion. Senaste
varden ateranvands i nya paneler och skrivs aven till
den konfigurerade state-filen, eller defaultfilen `.an_print_panel_state.json`
i aktuell arbetsmapp, sa de finns kvar efter restart av kernel nar cellen kors
igen.

```python
panel = Panel(allmanna_barighetsekvationen)                  # anvand senaste varden
panel = Panel(allmanna_barighetsekvationen, key="fall_1")     # separat state per fall
panel = Panel(allmanna_barighetsekvationen, state_file="annan.json")
```

Nar en panel skapas laddas startvarden i denna ordning:

1. sparade varden for exakt samma funktion och `key`
2. senaste sparade panel for samma funktion i samma state-fil
3. defaultvarden fran `panel_schema`

Det betyder att ett nytt fall kan borja som kopia av foregaende panel for samma
funktion, men sparas separat nar den nya panelen har en egen `key`.

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

Redovisningsdelen i `Panel` ar blockspecifik och motsvarar anropen till
`CalcBlock.MB`, `CalcBlock.ID`, `CalcBlock.DR`, `CalcBlock.EKV` och
`CalcBlock.SR`.

Foreslagen struktur:

- `src/an_print` for block, layout, panel och senare exportfunktioner
- `tests/` for tester
- `notebooks/` for exempel och visuella prototyper
- `docs/` for dokumentation
