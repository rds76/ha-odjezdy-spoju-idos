from __future__ import annotations

from datetime import datetime, timedelta

import aiohttp
from bs4 import BeautifulSoup

from .connection_data import validate_response
from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_TIMEOUT,
    REGIONS,
    VEHICLE_TYPES,
    ATTR_CILOVA,
    ATTR_VYCHOZI,
    ATTR_LINKA,
    ATTR_PROSTREDEK,
    ATTR_ODJEZD,
    ATTR_ODJEZD_TS,
    ATTR_PRIJEZD,
    ATTR_PRIJEZD_TS,
    ATTR_SPOJ,
    ATTR_SPOJE,
    ATTR_UPDATED,
)

import logging

_LOGGER = logging.getLogger(__name__)

class IdosScraper:

    MAX_REQUESTS = 5

    def __init__(self, hass: HomeAssistant, session, region_id):
        self.hass = hass
        self.session = session
        region = REGIONS[region_id]
        self.base_url = region["url"]
        self.parser = region.get("parser", 1)
        self.prostredek = region.get("prostredek", "")

    async def get_connections(
        self,
        source: str,
        destination: str,
        search_dt: datetime,
        count: int,
    ) -> dict:

        _LOGGER.info("Loading and scraping %d connection(s) from IDOS: '%s -> %s' since: %s", count, source, destination, search_dt.strftime("%Y-%m-%d %H:%M:%S"))

        spoje = []
        requests = 0

        previous_departure = 0

        while len(spoje) < count and requests < self.MAX_REQUESTS:

            requests += 1

            params = {
                "date": search_dt.strftime("%d.%m.%Y"),
                "time": search_dt.strftime("%H:%M"),
                "f": source,
                "t": destination,
                "direct": "true",
                "submit": "true",
            }

            async with self.session.get(
                self.base_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as response:

                response.raise_for_status()
                html = await response.text()
                _LOGGER.debug("URL: %s", response.url)

            batch = await self.hass.async_add_executor_job(self._parse_connections, html)

            if not batch:
                _LOGGER.warning("IDOS returned no connections, stopping pagination")
                break

            #
            # odstranění duplicit při navazujících dotazech
            #
            existing = {spoj[ATTR_ODJEZD_TS] for spoj in spoje}

            for spoj in batch:
                if spoj[ATTR_ODJEZD_TS] not in existing:
                    spoje.append(spoj)

            if len(spoje) >= count:
                break

            last_departure = batch[-1][ATTR_ODJEZD_TS]

            if last_departure <= previous_departure:
                _LOGGER.warning("Departure timestamp did not advance, stopping pagination")
                break

            previous_departure = last_departure

            #
            # další hledání od minuty po posledním spoji
            #
            search_dt = datetime.fromtimestamp(last_departure, dt_util.DEFAULT_TIME_ZONE) + timedelta(minutes=1)

            _LOGGER.debug("Need more connections (%d/%d), continuing from %s", len(spoje), count, search_dt)

        if not spoje:
            raise ValueError("No connections found")

        spoje = spoje[:count]

        data = {
            ATTR_UPDATED: datetime.now(dt_util.DEFAULT_TIME_ZONE),
            ATTR_VYCHOZI: source,
            ATTR_CILOVA: destination,
            ATTR_SPOJE: spoje,
        }

        validate_response(data)

        return data

    def _parse_connections(self, html: str) -> list:

        if self.parser == 1:
            return self._parse_connections_v1(html)

        if self.parser == 2:
            return self._parse_connections_v2(html)

        raise ValueError(f"Unsupported parser version: {self.parser}")

    def _parse_connections_v1(self, html: str) -> list:
        """Parse connection-table based IDOS layout."""

        soup = BeautifulSoup(html, "html.parser")

        tables = soup.select("table.results")

        result = []

        reference_dt = datetime.now(dt_util.DEFAULT_TIME_ZONE)

        for table in tables:

            rows = table.select("tr.datarow")

            if len(rows) < 2:
                continue

            try:

                row0 = rows[0].find_all("td", recursive=False)
                row1 = rows[1].find_all("td", recursive=False)

                date = row0[1].get_text(strip=True)

                odjezd = row0[4].get_text(strip=True)
                prijezd = row1[3].get_text(strip=True)

                odjezd_dt = datetime.strptime(f"{date}{reference_dt.year} {odjezd}:00", "%d.%m.%Y %H:%M:%S").replace(tzinfo=reference_dt.tzinfo)
                prijezd_dt = datetime.strptime(f"{date}{reference_dt.year} {prijezd}:00", "%d.%m.%Y %H:%M:%S").replace(tzinfo=reference_dt.tzinfo)

                odjezd_dt = self._normalize_schedule_datetime(odjezd_dt, reference_dt)
                prijezd_dt = self._normalize_schedule_datetime(prijezd_dt, reference_dt)

                prijezd_dt = self._normalize_arrival_datetime(odjezd_dt, prijezd_dt)


                from_stop = row0[2].get_text(strip=True)
                to_stop = row1[2].get_text(strip=True)

                cell = row0[6]

                line_a = cell.find("a")
                linka = line_a.get_text(strip=True) if line_a else "-"

                vehicle_img = cell.find("img")
                if vehicle_img:
                    prostredek = vehicle_img.get("title") or vehicle_img.get("alt") or ""
                    prostredek = VEHICLE_TYPES.get(prostredek.lower(), prostredek)
                else:
                    prostredek = ""

                result.append(
                    {
                        ATTR_ODJEZD: odjezd,
                        ATTR_ODJEZD_TS: int(odjezd_dt.timestamp()),
                        ATTR_PRIJEZD: prijezd,
                        ATTR_PRIJEZD_TS: int(prijezd_dt.timestamp()),
                        ATTR_LINKA: linka,
                        ATTR_PROSTREDEK: prostredek,
                        ATTR_SPOJ: f"{from_stop}->{to_stop}",
                    }
                )

            except Exception as exc:
                _LOGGER.debug("Unable to parse connection: %s", exc)

        return result

    def _parse_connections_v2(self, html: str) -> list:
        """Parse connection-list based IDOS layout."""

        soup = BeautifulSoup(html, "html.parser")

        result = []

        reference_dt = datetime.now(dt_util.DEFAULT_TIME_ZONE)

        for conn in soup.select("div.connection-list > div.connection"):

            try:
                #
                # Linka
                #
                line_el = conn.select_one("div.line-title h3 span")

                line_text = (
                    line_el.get_text(strip=True)
                    if line_el
                    else ""
                )

                prostredek = ""
                linka = "-"

                if self.prostredek:
                    linka = line_text
                    prostredek = self.prostredek
                else:
                    parts = line_text.split(" ", 1)

                    if len(parts) > 1:
                        prostredek = parts[0]
                        linka = parts[1]
                    elif line_text:
                        linka = line_text

                #
                # Odjezd / příjezd
                #
                stations = conn.select("ul.stations li.item")

                if len(stations) < 2:
                    continue

                departure_station = stations[0]
                arrival_station = stations[-1]

                odjezd = departure_station.select_one("p.time").get_text(strip=True)

                prijezd = arrival_station.select_one("p.time").get_text(strip=True)

                #
                # Datum
                #
                date_el = conn.select_one("div.connection-head h2.date span.date-after")

                if not date_el:
                    continue

                #
                # "1.11. ne" -> "1.11."
                #
                date = date_el.get_text(strip=True).split()[0]

                odjezd_dt = datetime.strptime(f"{date}{reference_dt.year} {odjezd}:00", "%d.%m.%Y %H:%M:%S").replace(tzinfo=reference_dt.tzinfo)
                prijezd_dt = datetime.strptime(f"{date}{reference_dt.year} {prijezd}:00","%d.%m.%Y %H:%M:%S").replace(tzinfo=reference_dt.tzinfo)

                odjezd_dt = self._normalize_schedule_datetime(odjezd_dt, reference_dt)
                prijezd_dt = self._normalize_schedule_datetime(prijezd_dt, reference_dt)

                prijezd_dt = self._normalize_arrival_datetime(odjezd_dt, prijezd_dt)

                from_stop = departure_station.select_one("strong.name").get_text(strip=True)
                to_stop = arrival_station.select_one("strong.name").get_text(strip=True)

                result.append(
                    {
                        ATTR_LINKA: linka,
                        ATTR_PROSTREDEK: prostredek,
                        ATTR_ODJEZD: odjezd,
                        ATTR_ODJEZD_TS: int(odjezd_dt.timestamp()),
                        ATTR_PRIJEZD: prijezd,
                        ATTR_PRIJEZD_TS: int(prijezd_dt.timestamp()),
                        ATTR_SPOJ: f"{from_stop}->{to_stop}",
                    }
                )

            except Exception as exc:
                _LOGGER.debug("Unable to parse connection: %s", exc)

        return result

    def _normalize_schedule_datetime(self, dt: datetime, reference: datetime) -> datetime:
        """
        Convert IDOS partial date to real date.

        Handles year rollover.
        """

        if dt < reference - timedelta(days=1):
            return dt.replace(year=dt.year + 1)

        return dt

    def _normalize_arrival_datetime(self, departure_dt: datetime, arrival_dt: datetime) -> datetime:
        """Handle midnight rollover."""

        if arrival_dt < departure_dt:
            arrival_dt += timedelta(days=1)

        return arrival_dt