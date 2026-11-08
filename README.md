<p align="center">
  <img src="custom_components/jr_idos/brand/icon.png" width="128" alt="JR-IDOS">
</p>

# Odjezdy spojů IDOS

[![GitHub release](https://img.shields.io/github/v/release/rds76/ha-odjezdy-spoju-idos)](https://github.com/rds76/ha-odjezdy-spoju-idos/releases/latest)
[![GitHub License](https://img.shields.io/github/license/rds76/ha-odjezdy-spoju-idos)](LICENSE)
![GitHub Validate](https://img.shields.io/github/actions/workflow/status/rds76/ha-odjezdy-spoju-idos/validate.yaml?label=validate)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?logo=homeassistant&logoColor=white)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rds76&repository=ha-odjezdy-spoju-idos&category=integration)
[![GitHub stars](https://img.shields.io/github/stars/rds76/ha-odjezdy-spoju-idos?style=social)](https://github.com/rds76/ha-odjezdy-spoju-idos/stargazers)

Home Assistant integrace pro zobrazení nadcházejících odjezdů veřejné dopravy z portálu IDOS.

<p align="center">
  <img src="assets/odjezdy-spoju-light.png" width="48%" alt="Karta Odjezdy spojů IDOS – světlý režim">
  <img src="assets/odjezdy-spoju-dark.png" width="48%" alt="Karta Odjezdy spojů IDOS – tmavý režim">
</p>

Integrace je vhodná například pro sledování odjezdů z místa bydliště, pracoviště, školy nebo jiné často používané zastávky. Automaticky zobrazuje nejbližší přímé spoje mezi dvěma zvolenými zastávkami a plánuje aktualizace podle skutečných časů odjezdů.

> Tato integrace není oficiálně spojena se službou IDOS.

## Funkce

- Konfigurace přes uživatelské rozhraní Home Assistantu (Config Flow)
- Podpora více oblastí IDOS
- Zobrazení více následujících spojů
- Automatická aktualizace před odjezdem nejbližšího spoje
- Čeština a angličtina
- Optimalizovaný počet dotazů na IDOS
- Vlastní Lovelace karta s odpočtem do odjezdu (součástí integrace)

## Podporované oblasti

- IDS Jihomoravského kraje
- Pražská integrovaná doprava
- IDS Moravskoslezského kraje
- IDS Olomouckého kraje
- Vlaky

Další oblasti mohou být doplněny na vyžádání.

## Požadavky

Home Assistant 2024.7.0 nebo novější.

## Instalace přes HACS

1. Otevřete **HACS → Integrations**.
2. Přidejte tento repozitář jako **Custom Repository** typu **Integration**.
3. Nainstalujte integraci.
4. Restartujte Home Assistant.
5. Přidejte integraci přes **Nastavení → Zařízení a služby → Přidat integraci**.

## Ruční instalace

Zkopírujte adresář:

```text
custom_components/jr_idos
```

do:

```text
ha-config/custom_components/
```

Restartujte Home Assistant a přidejte integraci přes uživatelské rozhraní.

## Konfigurace

Při vytváření nové trasy lze nastavit:

| Položka | Popis |
|----------|----------|
| Název | Název trasy zobrazený v Home Assistantu |
| Oblast | IDS JMK, PID apod. |
| Výchozí zastávka | Nástupní zastávka |
| Cílová zastávka | Cílová zastávka |
| Počet spojů | Počet zobrazovaných následujících spojů |
| Offset | Jak dlouho před odjezdem má být spoj považován za aktuální |

### Zadávání zastávek

Názvy zastávek je nutné zadávat přesně tak, jak je používá IDOS.

Nejjednodušší je vyhledat požadované spojení přímo na webu IDOS a zkopírovat názvy zastávek z formuláře.

Pokud název zastávky neodpovídá názvu používanému IDOSem, nemusí být nalezeno žádné spojení.

> **Tip:** Ověřte si nejprve vyhledání spojení přímo v IDOSu. Pokud spojení funguje v IDOSu, bude fungovat i v integraci.

### Důležité

Integrace používá vyhledání **přímého** spojení mezi výchozí a cílovou zastávkou.

Nejlépe se hodí pro pravidelně používané trasy, například:

- domov → centrum města
- domov → práce
- domov → nádraží
- domov → škola

Příklad:

```text
Výchozí zastávka: Výstaviště
Cílová zastávka: Hlavní
```

Integrace pak zobrazuje nejbližší odjezdy z oblasti Výstaviště směrem do centra města.

## Vytvářené entity

Pro každou trasu vznikne hlavní entita:

```text
sensor.vystaviste
```

a dále entity jednotlivých spojů:

```text
sensor.vystaviste_1
sensor.vystaviste_2
sensor.vystaviste_3
...
```

Každá entita spoje obsahuje například:

- linku
- čas odjezdu
- čas příjezdu
- popis spoje
- timestamp odjezdu
- timestamp příjezdu

Karta používá hlavní entitu, která nese atributy všech zobrazených spojů.

## Jak funguje aktualizace

Integrace nepoužívá pevný interval obnovování.

Po načtení spojů automaticky vypočítá nejvhodnější okamžik další aktualizace podle odjezdu nejbližšího spoje. Díky tomu výrazně snižuje počet požadavků vůči službě IDOS.

## Lovelace karta

Integrace obsahuje vlastní kartu `custom:jr-idos-card`. Registruje se automaticky, není potřeba přidávat žádný zdroj. Po první instalaci restartujte Home Assistant a obnovte stránku v prohlížeči (Ctrl+Shift+R).

Kartu lze přidat přes editor dashboardu (**Přidat kartu → Odjezdy spojů IDOS**) nebo v YAML:

```yaml
type: custom:jr-idos-card
entity: sensor.vystaviste
color_strip: true
```

| Volba | Popis |
|-------|-------|
| `entity` | Hlavní entita trasy (např. `sensor.vystaviste`), ne entity jednotlivých spojů |
| `color_strip` | Barevný pruh vlevo, podle kterého lze odlišit více tras. Výchozí `false` |

### Zvýraznění spoje

Karta zvýrazňuje první spoj podle času, který zbývá na vyražení, s ohledem na nastavený `offset` (čas na cestu k zastávce):

- **oranžově**, pokud do odjezdu zbývá méně než 15 min + offset,
- **červeně**, pokud zbývá méně než 8 min + offset.

Pruh nad seznamem spojů ukazuje stejný časový úsek. Časy delší než hodina se zobrazují jako `1:29 h`.

## Známá omezení

- Integrace využívá HTML scraping veřejně dostupných stránek IDOS.
- Změna struktury stránek IDOS může vyžadovat úpravu parseru.
- Dostupnost dat závisí na dostupnosti služby IDOS.

## Licence

Tento projekt je distribuován pod licencí MIT.
