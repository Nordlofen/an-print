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
