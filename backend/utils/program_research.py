import os
import re
import asyncio
import logging
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx

from backend.models.schemas import ApplicationTarget
from backend.utils.json_parse import parse_llm_json

logger = logging.getLogger(__name__)


@dataclass
class ResearchSource:
    url: str
    title: str
    text: str
    source_type: str


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = dict(attrs)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "a":
            self._current_href = attrs_dict.get("href")
            self._current_link_text = []

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._current_href:
            text = " ".join(self._current_link_text).strip()
            self.links.append((self._current_href, text))
            self._current_href = None
            self._current_link_text = []

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._in_title:
            self.title += f" {text}"
        elif self._current_href:
            self._current_link_text.append(text)
        self.text_parts.append(text)

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.text_parts)).strip()


def _looks_official(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host.endswith(".edu") or ".edu." in host or any(
        marker in host for marker in ("college", "university", "school")
    )


def _same_site(url: str, seed_url: str) -> bool:
    return urlparse(url).netloc.lower() == urlparse(seed_url).netloc.lower()


def _source_type(url: str, text: str) -> str:
    blob = f"{url} {text}".lower()
    if any(term in blob for term in ("faculty", "people", "directory")):
        return "faculty_page"
    if "lab" in blob or "group" in blob:
        return "lab_page"
    if "research" in blob:
        return "research_page"
    return "program_page"


def _rank_links(links: Iterable[tuple[str, str]], base_url: str) -> list[str]:
    scored: list[tuple[int, str]] = []
    keywords = {
        "faculty": 8,
        "people": 8,
        "directory": 8,
        "research": 6,
        "labs": 5,
        "lab": 5,
        "group": 4,
        "areas": 4,
        "professor": 3,
    }
    for href, label in links:
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or not _same_site(absolute, base_url):
            continue
        haystack = f"{parsed.path} {label}".lower()
        score = sum(weight for word, weight in keywords.items() if word in haystack)
        if score:
            scored.append((score, absolute.split("#")[0]))
    return list(dict.fromkeys(url for _, url in sorted(scored, reverse=True)))


async def _fetch_page(client: httpx.AsyncClient, url: str) -> tuple[_PageParser, str]:
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    parser = _PageParser()
    parser.feed(response.text[:1_000_000])
    return parser, str(response.url)


def _search_query(target: ApplicationTarget) -> str:
    query_parts = [
        target.school_name,
        target.program_name,
        "official faculty research department",
    ]
    return " ".join(part for part in query_parts if part).strip()


def _dedupe_official_urls(urls: Iterable[str]) -> list[str]:
    clean_urls = []
    for url in urls:
        if not isinstance(url, str) or not url.strip():
            continue
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            continue
        if _looks_official(url):
            clean_urls.append(url)
    return list(dict.fromkeys(clean_urls))


def _vertex_grounded_search_sync(target: ApplicationTarget) -> list[str]:
    from google import genai
    from google.genai.types import GenerateContentConfig, GoogleSearch, HttpOptions, Tool

    query = _search_query(target)
    if not query:
        return []

    client = genai.Client(
        http_options=HttpOptions(api_version="v1"),
        vertexai=True,
        project=os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEXAI_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("VERTEXAI_LOCATION") or "global",
    )
    prompt = f"""Find official university webpages for this graduate program/faculty research target:
{query}

Return only JSON with this exact schema:
{{"urls":["https://official-department-or-faculty-url.edu/path"]}}

Rules:
- Prefer official department, program, faculty directory, lab, or research group pages.
- Do not include rankings, Wikipedia, social media, news, or third-party admissions pages.
- Include at most 5 URLs."""
    response = client.models.generate_content(
        model=os.getenv("STORYCOACH_SEARCH_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config=GenerateContentConfig(
            tools=[Tool(google_search=GoogleSearch())],
            temperature=1.0,
        ),
    )
    text = response.text or ""
    try:
        data = parse_llm_json(text)
        urls = data.get("urls", [])
    except Exception:
        urls = re.findall(r"https?://[^\s\"'<>),]+", text)
    return _dedupe_official_urls(urls)


async def _vertex_search_program_urls(target: ApplicationTarget) -> list[str]:
    if not (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEXAI_PROJECT")):
        logger.info("Program search skipped: GOOGLE_CLOUD_PROJECT/VERTEXAI_PROJECT is not set")
        return []
    try:
        urls = await asyncio.to_thread(_vertex_grounded_search_sync, target)
        logger.info("Vertex program search returned %d official URL(s)", len(urls))
        return urls
    except Exception as exc:
        logger.warning("Vertex program search failed: %s", exc)
        return []


async def _custom_search_program_urls(target: ApplicationTarget) -> list[str]:
    query = _search_query(target)
    if not query:
        return []

    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_CX")
    if not api_key or not cx:
        logger.info("Custom Search skipped: GOOGLE_SEARCH_API_KEY/GOOGLE_SEARCH_CX is not set")
        return []

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": api_key, "cx": cx, "q": query, "num": 5},
        )
        response.raise_for_status()
        data = response.json()
    urls = [item.get("link", "") for item in data.get("items", [])]
    return _dedupe_official_urls(urls)


async def _search_program_urls(target: ApplicationTarget) -> list[str]:
    urls = await _vertex_search_program_urls(target)
    return urls or await _custom_search_program_urls(target)


async def research_program_sources(target: ApplicationTarget, max_pages: int = 8) -> list[ResearchSource]:
    seed_urls = [target.program_url.strip()] if target.program_url.strip() else []
    if not seed_urls:
        seed_urls = await _search_program_urls(target)

    logger.info("Program research starting with %d seed URL(s)", len(seed_urls))
    sources: list[ResearchSource] = []
    seen: set[str] = set()
    async with httpx.AsyncClient(
        timeout=20,
        headers={"User-Agent": "StoryCoach academic application research bot/0.1"},
    ) as client:
        for seed_url in seed_urls[:5]:
            if not seed_url.startswith(("http://", "https://")):
                seed_url = f"https://{seed_url}"
            queue = [seed_url]
            while queue and len(sources) < max_pages:
                url = queue.pop(0)
                if url in seen:
                    continue
                seen.add(url)
                try:
                    parser, final_url = await _fetch_page(client, url)
                except Exception as exc:
                    logger.info("Program research skipped URL %s: %s", url, exc)
                    continue
                text = parser.text[:8000]
                if len(text) < 300:
                    logger.info("Program research skipped short page %s", final_url)
                    continue
                sources.append(
                    ResearchSource(
                        url=final_url,
                        title=parser.title.strip(),
                        text=text,
                        source_type=_source_type(final_url, text[:1000]),
                    )
                )
                queue.extend(_rank_links(parser.links, final_url)[:6])
    logger.info("Program research retrieved %d source page(s)", len(sources))
    return sources


def sources_prompt_block(sources: list[ResearchSource]) -> str:
    if not sources:
        return "No verified program sources were retrieved. Do not invent faculty or program facts."
    blocks = []
    for i, source in enumerate(sources, 1):
        blocks.append(
            f"[Source {i}] {source.source_type}\n"
            f"Title: {source.title or 'Untitled'}\n"
            f"URL: {source.url}\n"
            f"Text excerpt: {source.text[:2500]}"
        )
    return "\n\n".join(blocks)
