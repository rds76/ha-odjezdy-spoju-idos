"""Sensor platform for Spoje IDOS."""

from __future__ import annotations

import time

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from datetime import datetime
from homeassistant.util.dt import (
    DEFAULT_TIME_ZONE,
)

from .const import (
    DOMAIN,
    DEVICE_NAME_PREFIX,
    MANUFACTURER,
    MODEL,
    CONF_CONNECTIONS,
    DEFAULT_CONNECTIONS,
    ATTR_CILOVA,
    ATTR_LINKA,
    ATTR_LINKA_TEXT,
    ATTR_ODJEZD,
    ATTR_ODJEZD_TS,
    ATTR_POCET_SPOJU,
    ATTR_PORADI,
    ATTR_PRIJEZD,
    ATTR_PRIJEZD_TS,
    ATTR_SPOJ,
    ATTR_SPOJE,
    ATTR_UPDATED,
    ATTR_VYCHOZI,
    ICON_CONNECTION,
    ICON_ROUTE,
    TEXTS,
)


async def async_setup_entry(hass, entry,async_add_entities):
    """Setup sensors."""

    coordinator = hass.data[DOMAIN][entry.entry_id]
    count = int(
        entry.options.get(
            CONF_CONNECTIONS,
            entry.data.get(CONF_CONNECTIONS, DEFAULT_CONNECTIONS),
        )
    )

    entities = [JrRouteSensor(coordinator, entry)]

    for idx in range(count):
        entities.append(
            JrConnectionSensor(
                coordinator,
                entry,
                idx,
            )
        )

    async_add_entities(entities)


class JrBaseEntity(CoordinatorEntity):
    """Base entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)

        self.entry = entry

    @property
    def device_info(self):
        """Group all sensors into one device."""

        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": f"{DEVICE_NAME_PREFIX} {self.entry.title}",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def texts(self):
        lang = self.hass.config.language or "en"
        return TEXTS.get(lang, TEXTS["en"])


class JrRouteSensor(JrBaseEntity, SensorEntity):
    """Main route sensor."""

    _attr_icon = ICON_ROUTE
    _attr_device_class =  SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)

        self._attr_name = None

        self._attr_unique_id = f"{entry.entry_id}_route"

    @property
    def native_value(self):
        """Last successful refresh timestamp."""

        if not self.coordinator.data:
            return None

        return self.coordinator.data.get(ATTR_UPDATED)


    @property
    def available(self):
        return self.coordinator.data is not None

    @property
    def extra_state_attributes(self):
        """Expose complete route information."""

        data = self.coordinator.data

        if not data:
            return {}

        return {
            ATTR_UPDATED: data.get(ATTR_UPDATED),
            ATTR_VYCHOZI: data.get(ATTR_VYCHOZI),
            ATTR_CILOVA: data.get(ATTR_CILOVA),
            ATTR_POCET_SPOJU: len(data.get(ATTR_SPOJE,[])),
            ATTR_SPOJE: data.get(ATTR_SPOJE,[]),
        }


class JrConnectionSensor(JrBaseEntity, SensorEntity):
    """Single IDOS connection."""

    _attr_icon = ICON_CONNECTION
    _attr_native_unit_of_measurement = "min"
    _attr_suggested_display_precision = 0
    _attr_state_class = None

    def __init__(self, coordinator, entry, index):
        super().__init__(coordinator, entry)

        self.index = index

        self._attr_name = f"{index + 1}"

        self._attr_unique_id = (
            f"{entry.entry_id}"
            f"_connection_"
            f"{index + 1}"
        )

    async def async_added_to_hass(self):
        """Register for minute refresh."""

        await super().async_added_to_hass()

        self.coordinator.register_minute_entity(self)

    async def async_will_remove_from_hass(self):
        """Cleanup."""

        self.coordinator.unregister_minute_entity(self)

        await super().async_will_remove_from_hass()

    def _connection(self):
        """Return connection matching this sensor."""

        data = self.coordinator.data

        if not data:
            return None

        spoje = data.get(ATTR_SPOJE,[])

        if (self.index >= len(spoje)):
            return None

        return spoje[self.index]

    @property
    def available(self):
        return (
            self._connection()
            is not None
        )

    @property
    def native_value(self):
        """Minutes until departure."""

        spoj = self._connection()

        if not spoj:
            return None

        departure_ts = spoj.get(ATTR_ODJEZD_TS)

        if departure_ts is None:
            return None

        minutes = round(departure_ts - time.time()) / 60

        return max(minutes,0)

    @property
    def extra_state_attributes(self):
        """Connection details."""

        spoj = self._connection()

        if not spoj:
            return {}

        odjezd_ts = spoj.get(ATTR_ODJEZD_TS)
        prijezd_ts = spoj.get(ATTR_PRIJEZD_TS)

        return {
            ATTR_PORADI: self.index + 1,
            ATTR_LINKA: spoj.get(ATTR_LINKA),
            ATTR_LINKA_TEXT: f"{self.texts['line']}: {spoj.get(ATTR_LINKA)}",
            ATTR_ODJEZD: spoj.get(ATTR_ODJEZD),
            ATTR_ODJEZD_TS: datetime.fromtimestamp(odjezd_ts, DEFAULT_TIME_ZONE).isoformat()  if odjezd_ts else None,
            ATTR_PRIJEZD: spoj.get(ATTR_PRIJEZD),
            ATTR_PRIJEZD_TS: datetime.fromtimestamp(prijezd_ts, DEFAULT_TIME_ZONE).isoformat() if prijezd_ts else None,
            ATTR_SPOJ: spoj.get(ATTR_SPOJ),
        }