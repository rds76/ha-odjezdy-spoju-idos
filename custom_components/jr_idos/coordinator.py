"""Coordinator for Spoje IDOS."""

from __future__ import annotations

import logging
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

from aiohttp import ClientError
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import (
    async_get_clientsession,
)
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_utc_time_change,
)
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .idos import IdosScraper
from .connection_data import first_departure_timestamp

from .const import (
    CONF_DESTINATION,
    CONF_OFFSET,
    CONF_SOURCE,
    CONF_CONNECTIONS,
    FALLBACK_REFRESH_MINUTES,
    CONF_REGION,
    MINUTE_ROLLOVER_BUFFER_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class JrIdosCoordinator(DataUpdateCoordinator):
    """Coordinator handling all IDOS data."""

    def __init__(self, hass, entry) -> None:

        self.hass = hass
        self.entry = entry

        session = async_get_clientsession(hass)

        # self.api = JrIdosApi(session)

        self.api = IdosScraper(session, entry.data.get(CONF_REGION, "idsjmk"))


        #
        # Spojové entity registrují samy sebe,
        # aby jim šel každou minutu překreslit state
        # bez HTTP requestu.
        #
        self._minute_entities = set()

        self._unsub_refresh = None

        self._unsub_minute = (
            async_track_utc_time_change(
                hass,
                self._minute_tick,
                second=1,
            )
        )


        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=None,
        )

    async def _async_update_data(self):
        """Load fresh data."""

        #
        # IDOS accepts only HH:MM.
        # Add one extra minute and a small buffer so the
        # currently displayed departure disappears from results.
        #
        offset_minutes=int(self.entry.options.get(CONF_OFFSET, self.entry.data.get(CONF_OFFSET, 4)))
        search_dt = datetime.now(dt_util.DEFAULT_TIME_ZONE) + timedelta(minutes=offset_minutes + 1, seconds=MINUTE_ROLLOVER_BUFFER_SECONDS + 1)
        count=int(self.entry.options.get(CONF_CONNECTIONS, self.entry.data.get(CONF_CONNECTIONS, 3)))

        try:
            data = await self.api.get_connections(
              self.entry.data[CONF_SOURCE],
              self.entry.data[CONF_DESTINATION],
              search_dt,
              count,
            )
            self._schedule_next_refresh(data)
            return data

        except (ClientError, TimeoutError, ValueError) as err:
            _LOGGER.warning("Unable to load IDOS data: %s", err)
            self._schedule_next_refresh(None)
            return self.data

    def _schedule_next_refresh(self, data) -> None:
        """
        Schedule next refresh.

        Refresh is performed when
        the first displayed connection
        becomes obsolete.
        """

        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        #
        # No connection.
        # Retry in FALLBACK_REFRESH_MINUTES.
        #
        now = datetime.now(dt_util.DEFAULT_TIME_ZONE)

        if data is None:

            refresh_time = now + timedelta(minutes=FALLBACK_REFRESH_MINUTES)
            _LOGGER.info("[%s] No connections available, refresh planned at %s", self.entry.title, refresh_time)

        else:

            first_departure = first_departure_timestamp(data)

            if first_departure is None:

                _LOGGER.warning("[%s] No first departure found in payload", self.entry.title)
                refresh_time = now + timedelta(minutes=FALLBACK_REFRESH_MINUTES)

            else:

                offset = self.entry.options.get(CONF_OFFSET, self.entry.data.get(CONF_OFFSET, 4))
                # nacitame par sec pred koncem offsetu
                refresh_time = datetime.fromtimestamp(first_departure, dt_util.DEFAULT_TIME_ZONE) - timedelta(minutes=offset, seconds=MINUTE_ROLLOVER_BUFFER_SECONDS)
                #
                # Safety guard.
                #

                if refresh_time <= now:
                    refresh_time = (now + timedelta(minutes=1))

                _LOGGER.debug("[%s] First departure: %s", self.entry.title, datetime.fromtimestamp(first_departure, dt_util.DEFAULT_TIME_ZONE))
                _LOGGER.info("[%s] Next refresh planned at %s", self.entry.title, refresh_time)

        self._unsub_refresh = (
            async_track_point_in_time(
                self.hass,
                self._scheduled_refresh,
                refresh_time,
            )
        )

    async def _scheduled_refresh(self, *_) -> None:
        """Refresh callback."""

        _LOGGER.info("[%s] Executing scheduled refresh", self.entry.title)

        await self.async_request_refresh()

    @callback
    def register_minute_entity(self, entity) -> None:
        """Register entity for local minute updates."""

        self._minute_entities.add(entity)

    @callback
    def unregister_minute_entity(self, entity) -> None:
        """Remove entity."""

        self._minute_entities.discard(entity)

    @callback
    def _minute_tick(self, *_) -> None:
        """
        Local countdown refresh.

        No HTTP requests.
        Only redraw states.
        """

        for entity in (self._minute_entities):
            entity.async_write_ha_state()

    async def async_shutdown(self) -> None:
        """Cleanup."""

        if self._unsub_refresh:
            self._unsub_refresh()

        if self._unsub_minute:
            self._unsub_minute()