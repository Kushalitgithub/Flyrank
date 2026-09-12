"""Polite three-page scraper for the Books to Scrape practice site."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError


BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
OUTPUT_FILE = Path("books.json")
ERROR_FILE = Path("scrape_errors.json")
REQUEST_DELAY_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 15
HEADERS = {
	"User-Agent": "FlyrankAssignmentScraper/1.0 (educational; contact: student@example.com)"
}


class Book(BaseModel):
	"""The clean record written to the output JSON file."""

	model_config = ConfigDict(extra="forbid")

	title: str = Field(min_length=1)
	price_gbp: float = Field(ge=0)
	availability: str = Field(min_length=1)
	rating: int = Field(ge=0, le=5)
	url: HttpUrl


def parse_price(raw_price: str) -> float:
	"""Turn text such as '£51.77' into a number."""
	match = re.search(r"\d+(?:\.\d+)?", raw_price.replace(",", ""))
	if not match:
		raise ValueError(f"invalid price: {raw_price!r}")
	return float(match.group())


def parse_rating(card: Any) -> int:
	rating_names = {
		"Zero": 0,
		"One": 1,
		"Two": 2,
		"Three": 3,
		"Four": 4,
		"Five": 5,
	}
	rating_element = card.select_one(".star-rating")
	if not rating_element:
		raise ValueError("missing rating")

	for class_name in rating_element.get("class", []):
		if class_name in rating_names:
			return rating_names[class_name]
	raise ValueError("unknown rating")


def parse_book(card: Any) -> Book:
	title_element = card.select_one("h3 a")
	price_element = card.select_one(".price_color")
	availability_element = card.select_one(".availability")

	if not title_element or not price_element or not availability_element:
		raise ValueError("book card is missing a required field")

	relative_url = title_element.get("href")
	if not relative_url:
		raise ValueError("book card is missing a URL")

	return Book(
		title=title_element.get("title") or title_element.get_text(strip=True),
		price_gbp=parse_price(price_element.get_text()),
		availability=" ".join(availability_element.get_text(" ", strip=True).split()),
		rating=parse_rating(card),
		url="https://books.toscrape.com/catalogue/" + relative_url.lstrip("/")
		if not relative_url.startswith("http")
		else relative_url,
	)


def fetch_page(page_number: int, session: requests.Session) -> list[Book]:
	response = session.get(
		BASE_URL.format(page_number),
		headers=HEADERS,
		timeout=REQUEST_TIMEOUT_SECONDS,
	)
	response.raise_for_status()
	soup = BeautifulSoup(response.text, "html.parser")
	books = []
	for card in soup.select("article.product_pod"):
		books.append(parse_book(card))
	return books


def scrape_pages(page_numbers: range = range(1, 4)) -> tuple[list[Book], list[dict[str, str]]]:
	books: list[Book] = []
	errors: list[dict[str, str]] = []

	with requests.Session() as session:
		for position, page_number in enumerate(page_numbers):
			if position:
				time.sleep(REQUEST_DELAY_SECONDS)
			try:
				books.extend(fetch_page(page_number, session))
			except (requests.RequestException, ValidationError, ValueError) as error:
				errors.append({
					"page": str(page_number),
					"error": str(error),
				})

	return books, errors


def write_json(books: list[Book], errors: list[dict[str, str]]) -> None:
	OUTPUT_FILE.write_text(
		json.dumps([book.model_dump(mode="json") for book in books], indent=2),
		encoding="utf-8",
	)
	ERROR_FILE.write_text(json.dumps(errors, indent=2), encoding="utf-8")


def main() -> None:
	books, errors = scrape_pages()
	write_json(books, errors)
	print(f"Saved {len(books)} validated books to {OUTPUT_FILE}")
	if errors:
		print(f"Recorded {len(errors)} page error(s) in {ERROR_FILE}")


if __name__ == "__main__":
	main()
