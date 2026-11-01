from __future__ import annotations

from datetime import datetime, timedelta

import aiohttp
from bs4 import BeautifulSoup

from .idos_data import validate_response
from homeassistant.util import dt as dt_util

from .const import (    
    DEFAULT_TIMEOUT,
    REGIONS,
)

import logging

_LOGGER = logging.getLogger(__name__)

class IdosScraper:

    MAX_REQUESTS = 5

    def __init__(self, session, region):
        self.session = session
        self.base_url = REGIONS[region]["url"]

    async def get_connections(
        self,
        source: str,
        destination: str,
        search_dt: datetime,
        count: int,
    ) -> dict:

        _LOGGER.info("Loading and scraping connections from IDOS: '%s -> %s' starting from: %s", source, destination, search_dt)

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

            batch = self._parse_connections(html)

            if not batch:
                _LOGGER.warning("IDOS returned no connections, stopping pagination")
                break

            #
            # odstranění duplicit při navazujících dotazech
            #
            existing = {spoj["odjezd_ts"] for spoj in spoje}

            for spoj in batch:
                if spoj["odjezd_ts"] not in existing:
                    spoje.append(spoj)

            if len(spoje) >= count:
                break

            last_departure = batch[-1]["odjezd_ts"]

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
            "updated": datetime.now(dt_util.DEFAULT_TIME_ZONE),
            "vychozi": source,
            "cilova": destination,
            "spoje": spoje,
        }

        validate_response(data)

        return data
    

    def _parse_connections(self, html: str) -> list:

        soup = BeautifulSoup(html, "html.parser")

        tables = soup.select("table.results")

        result = []

        now = datetime.now()

        for table in tables:

            rows = table.select("tr.datarow")

            if len(rows) < 2:
                continue

            try:

                row0 = rows[0].find_all("td")
                row1 = rows[1].find_all("td")

                date = row0[1].get_text(strip=True)

                odjezd = row0[4].get_text(strip=True)
                prijezd = row1[3].get_text(strip=True)

                odjezd_dt = datetime.strptime(f"{date}{now.year} {odjezd}:00", "%d.%m.%Y %H:%M:%S")
                prijezd_dt = datetime.strptime(f"{date}{now.year} {prijezd}:00", "%d.%m.%Y %H:%M:%S")

                #
                # Přelom roku
                #
                if odjezd_dt < now - timedelta(days=1):
                    odjezd_dt = odjezd_dt.replace(year=odjezd_dt.year + 1)

                if prijezd_dt < now - timedelta(days=1):
                    prijezd_dt = prijezd_dt.replace(year=prijezd_dt.year + 1)

                from_stop = row0[2].get_text(strip=True)
                to_stop = row1[2].get_text(strip=True)

                line_a = row0[6].find("a")

                linka = (
                    line_a.get_text(strip=True)
                    if line_a
                    else ""
                )

                result.append(
                    {
                        "odjezd": odjezd,
                        "odjezd_ts": int(odjezd_dt.timestamp()),
                        "prijezd": prijezd,
                        "prijezd_ts": int(prijezd_dt.timestamp()),
                        "linka": linka,
                        "spoj": f"{from_stop}->{to_stop}",
                    }
                )

            except Exception:
                continue

        return result