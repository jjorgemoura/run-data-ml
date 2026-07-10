import logging
import re
import requests
import time
from collections import defaultdict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class DUVService:
    BASE_URL = "https://statistik.d-u-v.org"
    EVENT_LIST_URL      = f"{BASE_URL}/geteventlist.php"
    RESULT_EVENT_URL    = f"{BASE_URL}/getresultevent.php"
    RESULT_PERSON_URL   = f"{BASE_URL}/getresultperson.php"

    
    COUNTRY_RE = re.compile(r'^(.*?)\s*\(([A-Z]{2,4})\)\s*$')
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": BASE_URL,
    }

    def __init__(self) -> None:
        pass

    # PUBLIC Methods

    def fetch_races_from_athlete(self, athleteID):
        return [1, 5, 9]

    def fetch_all_athletes_of_event(self, eventID):
        return ""

    def find_event_by_name(self, eventName):
        return ""

    # INTERNAL Methods
    
    def fetch_all_events(self, max_pages: int = 1):
        all_events = []
        page = 1      # max is 119

        while True:
            if max_pages and page > max_pages:
                break

            logger.info("Fetching page %d...", page)
            events = self._fetch_event_list_page(page)

            if not events:
                logger.info("Empty page %d — done.", page)
                break

            all_events.extend(events)
            logger.info("  Page %d: %d events (total so far: %d)", page, len(events), len(all_events))
            page += 1


        return all_events
    
    def _fetch_event_list_page(self, page: int) -> list[dict]:
        """Fetch and parse one page of the DUV event list."""
        params = {
            "year":     "all",
            "dist":     "all",
            "country":  "all",
            "Language": "EN",
            "sort":     "1",
            "page":     page,
        }
        resp = self._get(self.EVENT_LIST_URL, params=params)
        if resp is None:
            logger.info("JM: GET returns nothing")
            return []
        return self._parse_event_list_page(resp.text)
    
    
    # PRIVATE Methods

    def _get(self, url: str, params: dict = None, delay: float = 1.0):
        try:
            resp = requests.get(url, params=params, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            time.sleep(delay)
            print(f"asdasd - {resp.url}")
            # logger.debug(" JM: URL is -> %s", resp.url)
            return resp
        except requests.RequestException as e:
            logger.warning("Request failed: %s — %s", url, e)
            return None

    def _parse_event_list_page(self, html: str) -> list[dict]:
        """
        Parse one page of geteventlist.php.
        Returns a list of raw event dicts.
        """
        soup = BeautifulSoup(html, "html.parser")
        events = []

        for row in soup.select("tr.odd, tr.even"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            link = row.find("a", href=re.compile(r"getresultevent\.php"))
            if not link:
                continue

            event_id_match = re.search(r"event=(\d+)", link["href"])
            if not event_id_match:
                continue

            date_raw   = cells[0].get_text(strip=True)
            name_raw   = cells[1].get_text(strip=True)
            dist_raw   = cells[2].get_text(strip=True)
            finish_raw = cells[3].get_text(strip=True)

            finishers = 0
            try:
                finishers = int(re.sub(r"[^\d]", "", finish_raw))
            except ValueError:
                pass

            # Extract year from date field (handles "28.-29.06.2025" and "12.04.2026")
            year_match = re.search(r"(\d{4})", date_raw)
            year = int(year_match.group(1)) if year_match else None

            events.append({
                "event_id":  int(event_id_match.group(1)),
                "date":      date_raw,
                "year":      year,
                "name_raw":  name_raw,
                "distance":  dist_raw,
                "finishers": finishers,
            })

        return events
