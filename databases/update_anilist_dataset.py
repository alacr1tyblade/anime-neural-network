import csv
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests

from parsing_dataset import (
    API_URL,
    CSV_FIELDS,
    MAX_PAGES_PER_BATCH,
    MAX_RETRIES,
    OUTPUT_PATH,
    REQUEST_INTERVAL_SECONDS,
    clean_description,
    make_row,
    retry_delay,
    write_dataset,
)


LOG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AnimeNeuralNetwork"
LOG_PATH = LOG_DIR / "update_anilist_dataset.log"
CHECK_INTERVAL_SECONDS = 14 * 24 * 60 * 60
ERROR_RETRY_SECONDS = 60 * 60

QUERY = """
query ($page: Int!, $perPage: Int!) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      hasNextPage
    }
    media(type: ANIME, sort: ID_DESC) {
      id
      title {
        english
        romaji
      }
      genres
      description(asHtml: false)
      meanScore
      popularity
      isAdult
    }
  }
}
"""

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def fetch_page(session: requests.Session, page_number: int) -> dict[str, Any]:
    request_body = {
        "query": QUERY,
        "variables": {"page": page_number, "perPage": 50},
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = session.post(API_URL, json=request_body, timeout=60)
        except requests.RequestException:
            if attempt == MAX_RETRIES:
                raise
            delay = retry_delay(attempt)
            logger.warning("Network error; retrying page %s in %ss", page_number, delay)
            time.sleep(delay)
            continue

        if response.status_code == 429 or response.status_code >= 500:
            if attempt == MAX_RETRIES:
                response.raise_for_status()
            delay = retry_delay(attempt, response)
            logger.warning(
                "AniList returned HTTP %s; retrying page %s in %ss",
                response.status_code,
                page_number,
                delay,
            )
            time.sleep(delay)
            continue

        if response.status_code >= 400:
            raise requests.HTTPError(
                f"AniList returned HTTP {response.status_code} on page "
                f"{page_number}: {response.text[:2000]}",
                response=response,
            )

        response.raise_for_status()
        payload = response.json()
        errors = payload.get("errors")
        if errors:
            rate_limited = any(
                isinstance(error, dict) and error.get("status") == 429
                for error in errors
            )
            if rate_limited and attempt < MAX_RETRIES:
                delay = retry_delay(attempt, response, rate_limited=True)
                logger.warning("AniList rate limit; retrying in %ss", delay)
                time.sleep(delay)
                continue
            raise RuntimeError(f"AniList GraphQL error: {errors}")

        data = payload.get("data")
        page_data = data.get("Page") if isinstance(data, dict) else None
        if not isinstance(page_data, dict):
            raise RuntimeError(f"AniList returned no data for page {page_number}")
        return page_data

    raise RuntimeError(f"Could not download page {page_number} after retries")


def load_dataset() -> tuple[list[dict[str, Any]], set[int], int, int]:
    if not OUTPUT_PATH.exists():
        raise FileNotFoundError(
            f"{OUTPUT_PATH.name} not found. Run parsing_dataset.py first."
        )

    with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames != CSV_FIELDS:
            raise RuntimeError(f"Unexpected columns in {OUTPUT_PATH.name}")
        rows = []
        cleaned_count = 0
        for row in reader:
            description = row.get("description") or ""
            cleaned = clean_description(description)
            if cleaned != description:
                cleaned_count += 1
            row["description"] = cleaned
            rows.append(dict(row))

    if not rows:
        raise RuntimeError(f"{OUTPUT_PATH.name} contains no anime records")

    ids = {int(row["id"]) for row in rows if row.get("id")}
    if not ids:
        raise RuntimeError(f"No valid AniList IDs found in {OUTPUT_PATH.name}")

    return rows, ids, max(ids), cleaned_count


def update_dataset() -> int:
    existing_rows, existing_ids, max_existing_id, cleaned_count = load_dataset()
    if cleaned_count:
        write_dataset(existing_rows, OUTPUT_PATH)
        logger.info("Cleaned HTML from %s existing descriptions", cleaned_count)

    new_rows = []
    new_ids = set()
    found_existing_title = False

    with requests.Session() as session:
        for page_number in range(1, MAX_PAGES_PER_BATCH + 1):
            page_data = fetch_page(session, page_number)
            media = page_data.get("media")
            page_info = page_data.get("pageInfo")

            if not isinstance(media, list) or not isinstance(page_info, dict):
                raise RuntimeError(f"Incomplete AniList response for page {page_number}")
            has_next_page = page_info.get("hasNextPage")
            if not isinstance(has_next_page, bool):
                raise RuntimeError(f"Missing pagination status on page {page_number}")

            for anime in media:
                anime_id = anime.get("id")
                if not isinstance(anime_id, int):
                    raise RuntimeError(f"Invalid anime ID on page {page_number}")
                if anime_id <= max_existing_id:
                    found_existing_title = True
                    break
                if anime_id not in existing_ids and anime_id not in new_ids:
                    new_ids.add(anime_id)
                    new_rows.append(make_row(anime))

            logger.info(
                "Checked page %s; found %s new titles so far",
                page_number,
                len(new_rows),
            )

            if found_existing_title or not has_next_page:
                break
            if page_number == MAX_PAGES_PER_BATCH:
                raise RuntimeError(
                    "More than 5,000 newer titles were found. "
                    "The update was not written; run a full dataset refresh."
                )
            time.sleep(REQUEST_INTERVAL_SECONDS)

    if new_rows:
        write_dataset(existing_rows + new_rows, OUTPUT_PATH)
        logger.info("Added %s new titles to %s", len(new_rows), OUTPUT_PATH.name)
    else:
        logger.info("No new titles found")

    return len(new_rows)


def main() -> None:
    configure_logging()
    try:
        while True:
            try:
                new_count = update_dataset()
            except (OSError, requests.RequestException, RuntimeError, ValueError):
                logger.exception("AniList dataset update failed")
                delay = ERROR_RETRY_SECONDS
                logger.info("Retrying in one hour")
            else:
                logger.info("Update complete; added %s titles", new_count)
                delay = CHECK_INTERVAL_SECONDS
                logger.info("Next check in 14 days")

            time.sleep(delay)
    except KeyboardInterrupt:
        logger.info("AniList updater stopped")


if __name__ == "__main__":
    main()
