"""Spoje IDOS integration."""

from __future__ import annotations

from pathlib import Path
import hashlib

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN, CARD_URL, CARD_FILE
from .coordinator import JrIdosCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]

def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:8]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    www = Path(__file__).parent / "www"
    card_hash = await hass.async_add_executor_job(_file_hash, www / CARD_FILE)

    await hass.http.async_register_static_paths(
        [StaticPathConfig(f"/{DOMAIN}", str(www), False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={card_hash}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    coordinator = JrIdosCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN,{})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    coordinator = hass.data[DOMAIN].pop(entry.entry_id,None)

    if coordinator:
        await coordinator.async_shutdown()

    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:

    await hass.config_entries.async_reload(entry.entry_id)

