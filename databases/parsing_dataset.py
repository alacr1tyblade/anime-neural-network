import csv
import json
import os
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests


API_URL = "https://graphql.anilist.co"
OUTPUT_PATH = Path(__file__).with_name("anime_data_anilist.csv")
PARTIAL_OUTPUT_PATH = OUTPUT_PATH.with_suffix(".partial.csv")
PROGRESS_PATH = OUTPUT_PATH.with_suffix(".progress.json")
PER_PAGE = 50
MAX_PAGE_DEPTH = 5000
MAX_PAGES_PER_BATCH = MAX_PAGE_DEPTH // PER_PAGE
REQUEST_INTERVAL_SECONDS = 2.1
CHECKPOINT_INTERVAL_PAGES = 10
MAX_RETRIES = 5

QUERY = """
query ($page: Int!, $perPage: Int!, $excludeIds: [Int] = []) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      hasNextPage
    }
    media(type: ANIME, sort: ID, id_not_in: $excludeIds) {
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

CSV_FIELDS = [
    "id",
    "title_english",
    "title_romaji",
    "genres",
    "description",
    "averageScore",
    "popularity",
    "isAdult",
]


class _DescriptionHTMLParser(HTMLParser):
    BLOCK_TAGS = {"br", "div", "li", "p", "blockquote", "hr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCK_TAGS and tag != "br":
            self.parts.append("\n")


def clean_description(description: str | None) -> str:
    if not description:
        return ""

    parser = _DescriptionHTMLParser()
    parser.feed(description)
    parser.close()
    text = "".join(parser.parts).replace("\xa0", " ")
    text = re.sub(r"<\s*/?\s*[A-Za-z][^>]*>", "", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def retry_delay(
    attempt: int,
    response: requests.Response | None = None,
    rate_limited: bool = False,
) -> float:
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 1.0)
            except ValueError:
                pass

        if response.status_code == 429:
            rate_limited = True

    if rate_limited:
        return 60.0

    return min(60.0, 2.0 ** (attempt + 1))


def fetch_page(
    session: requests.Session,
    page_number: int,
    excluded_ids: list[int],
) -> dict[str, Any]:
    request_body = {
        "query": QUERY,
        "variables": {
            "page": page_number,
            "perPage": PER_PAGE,
            "excludeIds": excluded_ids,
        },
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = session.post(API_URL, json=request_body, timeout=60)
        except requests.RequestException:
            if attempt == MAX_RETRIES:
                raise
            delay = retry_delay(attempt)
            print(f"Network error on page {page_number}; retrying in {delay:g}s")
            time.sleep(delay)
            continue

        if response.status_code == 429 or response.status_code >= 500:
            if attempt == MAX_RETRIES:
                response.raise_for_status()
            delay = retry_delay(attempt, response)
            print(
                f"AniList returned HTTP {response.status_code} "
                f"on page {page_number}; retrying in {delay:g}s"
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
                print(f"AniList rate limit on page {page_number}; retrying in {delay:g}s")
                time.sleep(delay)
                continue
            raise RuntimeError(
                f"AniList GraphQL error on page {page_number}: "
                f"{json.dumps(errors, ensure_ascii=False)}"
            )

        data = payload.get("data")
        page_data = data.get("Page") if isinstance(data, dict) else None
        if not isinstance(page_data, dict):
            raise RuntimeError(f"AniList returned no page data for page {page_number}")
        return page_data

    raise RuntimeError(f"Could not download page {page_number} after retries")


def make_row(anime: dict[str, Any]) -> dict[str, Any]:
    title = anime.get("title") or {}
    return {
        "id": anime.get("id"),
        "title_english": title.get("english") or "",
        "title_romaji": title.get("romaji") or "",
        "genres": json.dumps(anime.get("genres") or [], ensure_ascii=False),
        "description": clean_description(anime.get("description")),
        "averageScore": anime.get("meanScore"),
        "popularity": anime.get("popularity"),
        "isAdult": anime.get("isAdult"),
    }


def write_dataset(rows: list[dict[str, Any]], output_path: Path) -> None:
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        output_file.flush()
        os.fsync(output_file.fileno())

    os.replace(temporary_path, output_path)


def save_checkpoint(
    rows: list[dict[str, Any]],
    next_page: int,
    excluded_ids: list[int],
) -> None:
    write_dataset(rows, PARTIAL_OUTPUT_PATH)
    temporary_path = PROGRESS_PATH.with_suffix(PROGRESS_PATH.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as progress_file:
        json.dump(
            {"next_page": next_page, "exclude_ids": excluded_ids},
            progress_file,
        )
        progress_file.flush()
        os.fsync(progress_file.fileno())
    os.replace(temporary_path, PROGRESS_PATH)


def load_checkpoint() -> tuple[list[dict[str, Any]], set[str], int, list[int]]:
    if not PARTIAL_OUTPUT_PATH.exists() and not PROGRESS_PATH.exists():
        return [], set(), 1, []
    if not PARTIAL_OUTPUT_PATH.exists() or not PROGRESS_PATH.exists():
        raise RuntimeError(
            "Incomplete download checkpoint. Remove both "
            f"{PARTIAL_OUTPUT_PATH.name} and {PROGRESS_PATH.name} to restart."
        )

    with PROGRESS_PATH.open("r", encoding="utf-8") as progress_file:
        progress = json.load(progress_file)
    next_page = progress.get("next_page")
    if not isinstance(next_page, int) or next_page < 1:
        raise RuntimeError(f"Invalid page number in {PROGRESS_PATH.name}")

    with PARTIAL_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames != CSV_FIELDS:
            raise RuntimeError(f"Unexpected columns in {PARTIAL_OUTPUT_PATH.name}")
        rows = [dict(row) for row in reader]

    seen_ids = {row["id"] for row in rows if row.get("id")}
    excluded_ids = progress.get("exclude_ids")
    if excluded_ids is None:
        # Migrate checkpoints created before the ID-exclusion batching was added.
        excluded_ids = sorted(int(anime_id) for anime_id in seen_ids)
        next_page = 1
    elif not isinstance(excluded_ids, list) or not all(
        isinstance(anime_id, int) for anime_id in excluded_ids
    ):
        raise RuntimeError(f"Invalid excluded ID list in {PROGRESS_PATH.name}")

    return rows, seen_ids, next_page, excluded_ids


def main() -> None:
    all_rows, seen_ids, page_number, excluded_ids = load_checkpoint()
    if all_rows:
        print(
            f"Resuming from page {page_number} of the current batch; "
            f"{len(all_rows)} titles already saved"
        )

    with requests.Session() as session:
        while True:
            try:
                page_data = fetch_page(session, page_number, excluded_ids)
            except (requests.RequestException, RuntimeError):
                if all_rows:
                    save_checkpoint(all_rows, page_number, excluded_ids)
                raise

            media = page_data.get("media")
            page_info = page_data.get("pageInfo")

            if not isinstance(media, list) or not isinstance(page_info, dict):
                raise RuntimeError(f"Incomplete AniList response for page {page_number}")
            has_next_page = page_info.get("hasNextPage")
            if not isinstance(has_next_page, bool):
                raise RuntimeError(f"Missing pagination status on page {page_number}")
            if not media:
                if not has_next_page:
                    break
                raise RuntimeError(f"AniList returned an empty page at page {page_number}")

            for anime in media:
                anime_id = anime.get("id")
                anime_key = str(anime_id)
                if anime_id is not None and anime_key not in seen_ids:
                    seen_ids.add(anime_key)
                    all_rows.append(make_row(anime))

            if page_number == 1 or page_number % 10 == 0:
                print(f"Downloaded page {page_number}; collected {len(all_rows)} titles")

            if not has_next_page:
                break

            if page_number == MAX_PAGES_PER_BATCH:
                excluded_ids = sorted(int(anime_id) for anime_id in seen_ids)
                page_number = 1
            else:
                page_number += 1

            if page_number == 1 or (page_number - 1) % CHECKPOINT_INTERVAL_PAGES == 0:
                save_checkpoint(all_rows, page_number, excluded_ids)
            time.sleep(REQUEST_INTERVAL_SECONDS)

    write_dataset(all_rows, OUTPUT_PATH)
    if PARTIAL_OUTPUT_PATH.exists():
        PARTIAL_OUTPUT_PATH.unlink()
    if PROGRESS_PATH.exists():
        PROGRESS_PATH.unlink()
    print(f"Saved {len(all_rows)} titles to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
