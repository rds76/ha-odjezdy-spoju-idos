"""Constants for Spoje IDOS."""

from __future__ import annotations

DOMAIN = "jr_idos"

NAME = "Spoje IDOS"

MANUFACTURER = "Jízdní řády"
MODEL = "IDOS"
DEVICE_NAME_PREFIX = "Spoje"

#
# Config flow fields
#
CONF_NAME = "name"
CONF_SOURCE = "source"
CONF_DESTINATION = "destination"
CONF_CONNECTIONS = "connections"
CONF_OFFSET = "offset"

#
# Defaults
#
DEFAULT_CONNECTIONS = 3
DEFAULT_OFFSET = 4
#
# Regiony
#
CONF_REGION = "region"
REGIONS = {
    "idsjmk": {
        "name": "IDS Jihomoravského kraje",
        "url": "https://idsjmk.idos.cz/idsjmk/spojeni",
    },
    "idsjmk-v2": {
        "name": "IDS Jihomoravského kraje (v2)",
        "url": "https://idos.cz/idsjmk/spojeni/vysledky",
        "parser": 2
    },
    "pid": {
        "name": "Pražská integrovaná doprava",
        "url": "https://pid.idos.cz/spojeni",
    },
    "pid-v2": {
        "name": "Pražská integrovaná doprava (v2)",
        "url": "https://idos.cz/pid/spojeni/vysledky",
        "parser": 2
    },
    "odis-v2": {
        "name": "IDS Moravskoslezského kraje",
        "url": "https://idos.cz/odis/spojeni/vysledky",
        "parser": 2
    },
    "odisidsok-v2": {
        "name": "IDS Olomouckého kraje",
        "url": "https://idos.cz/idsok/spojeni/vysledky",
        "parser": 2
    },
    "vlaky-v2": {
        "name": "Vlaky",
        "url": "https://idos.cz/vlaky/spojeni/vysledky",
        "parser": 2,
        "prostredek": "Vlak",
    },
}

# config-flow helper
REGION_OPTIONS = [
    {
        "value": key,
        "label": region["name"],
    }
    for key, region in REGIONS.items()
]

#
# API
#
DEFAULT_TIMEOUT = 30

#
# Attributes
#
ATTR_SPOJE = "spoje"

ATTR_LINKA = "linka"
ATTR_LINKA_TEXT = "linka_text"
ATTR_PROSTREDEK  = "prostredek"

ATTR_ODJEZD = "odjezd"
ATTR_ODJEZD_TS = "odjezd_ts"

ATTR_PRIJEZD = "prijezd"
ATTR_PRIJEZD_TS = "prijezd_ts"

ATTR_SPOJ = "spoj"

ATTR_PORADI = "poradi"

ATTR_VYCHOZI = "vychozi"
ATTR_CILOVA = "cilova"

ATTR_POCET_SPOJU = "pocet_spoju"

ATTR_UPDATED = "updated"

#
# Coordinator
#
FALLBACK_REFRESH_MINUTES = 5
MINUTE_ROLLOVER_BUFFER_SECONDS = 10

#
# Icons
#
ICON_ROUTE = "mdi:bus-clock"
ICON_CONNECTION = "mdi:bus"
ICONS_CONNECTION = {
    "bus": "mdi:bus",
    "vlak": "mdi:train",
    "tram": "mdi:tram",
    "metro": "mdi:subway",
    "trol": "mdi:bus-electric",
}
#
# Texty
#
TEXTS = {
    "cs": {
        "line": "linka:",
    },
    "en": {
        "line": "line:",
    },
}
VEHICLE_TYPES = {
    "autobus": "Bus",
    "tramvaj": "Tram",
    "trolejbus": "Trol",
}