import asyncio
import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

from backend.models.schemas import (
    ApplicationTarget, FacultyDossier, Grant, Publication,
)
from backend.utils.json_parse import parse_llm_json
from backend.utils.program_research import ResearchSource
from backend.utils.throttle import acompletion_with_retry

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
NSF_API = "https://api.nsf.gov/services/v1/awards.json"
NIH_API = "https://api.reporter.nih.gov/v2/projects/search"

ATOM_NS = "{http://www.w3.org/2005/Atom}"
HTTP_TIMEOUT = 5.0
USER_AGENT = "StoryCoach faculty enrichment bot/0.1 (mailto:guandyjay@gmail.com)"


def _split_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in re.split(r"\s+", full_name.strip()) if p]
    if len(parts) < 2:
        return ("", parts[0] if parts else "")
    return (parts[0], parts[-1])


def _safe_int(value: object) -> int:
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return 0


async def arxiv_search(name: str, max_results: int = 5) -> list[Publication]:
    first, last = _split_name(name)
    if not last:
        return []
    query = f'au:"{first} {last}"'.strip() if first else f'au:"{last}"'
    params = {
        "search_query": query,
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(ARXIV_API, params=params)
            response.raise_for_status()
        root = ET.fromstring(response.text)
    except Exception as exc:
        logger.warning("arxiv_search failed for %s: %s", name, exc)
        return []

    publications: list[Publication] = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        title_el = entry.find(f"{ATOM_NS}title")
        published_el = entry.find(f"{ATOM_NS}published")
        id_el = entry.find(f"{ATOM_NS}id")
        if title_el is None or id_el is None:
            continue
        title = re.sub(r"\s+", " ", (title_el.text or "")).strip()
        url = (id_el.text or "").strip()
        arxiv_id = url.rsplit("/", 1)[-1] if url else ""
        year = _safe_int(published_el.text) if published_el is not None else 0
        publications.append(Publication(
            title=title,
            year=year,
            venue="arXiv",
            url=url,
            arxiv_id=arxiv_id,
        ))
    return publications


async def nsf_awards_search(name: str, max_results: int = 5) -> list[Grant]:
    first, last = _split_name(name)
    if not last:
        return []
    pi_name = f"{last},{first}".strip(",")
    params = {
        "pdPIName": pi_name,
        "printFields": "id,title,startDate,expDate,abstractText",
        "rpp": str(max_results),
    }
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(NSF_API, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.warning("nsf_awards_search failed for %s: %s", name, exc)
        return []

    awards = (data.get("response") or {}).get("award") or []
    grants: list[Grant] = []
    for award in awards[:max_results]:
        award_id = str(award.get("id") or "")
        grants.append(Grant(
            title=str(award.get("title") or "")[:300],
            agency="NSF",
            award_id=award_id,
            start_year=_safe_int(_extract_year(award.get("startDate"))),
            end_year=_safe_int(_extract_year(award.get("expDate"))),
            url=f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award_id}" if award_id else "",
        ))
    return grants


def _extract_year(date_str: object) -> str:
    if not isinstance(date_str, str) or not date_str:
        return ""
    match = re.search(r"\b(\d{4})\b", date_str)
    return match.group(1) if match else ""


async def nih_reporter_search(name: str, max_results: int = 5) -> list[Grant]:
    first, last = _split_name(name)
    if not last:
        return []
    full = f"{first} {last}".strip()
    body = {
        "criteria": {"pi_names": [{"any_name": full}]},
        "limit": max_results,
        "offset": 0,
    }
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.post(NIH_API, json=body)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.warning("nih_reporter_search failed for %s: %s", name, exc)
        return []

    grants: list[Grant] = []
    for project in (data.get("results") or [])[:max_results]:
        award_id = str(project.get("project_num") or "")
        grants.append(Grant(
            title=str(project.get("project_title") or "")[:300],
            agency="NIH",
            award_id=award_id,
            start_year=_safe_int(_extract_year(project.get("project_start_date"))),
            end_year=_safe_int(_extract_year(project.get("project_end_date"))),
            url=f"https://reporter.nih.gov/project-details/{project.get('appl_id')}" if project.get("appl_id") else "",
        ))
    return grants


_LISTING_SYSTEM_PROMPT = """Extract a structured list of faculty members from the supplied page text.
Rules:
- Return ONLY JSON: {"faculty":[{"name":"...","profile_url":"...","blurb":"..."}]}
- Use names as they appear on the page; do not invent.
- profile_url should be the absolute URL to that faculty member's page if visible in the text; otherwise empty string.
- blurb is a short (<=200 chars) excerpt of any research-interest text shown for that faculty.
- If no faculty are present, return {"faculty":[]}."""


async def _extract_faculty_listing(
    source: ResearchSource, max_faculty: int,
) -> list[dict]:
    user_message = (
        f"Listing source URL: {source.url}\n"
        f"Title: {source.title}\n\n"
        f"--- PAGE TEXT (truncated) ---\n{source.text[:6000]}\n--- END ---\n\n"
        f"Return at most {max_faculty} faculty entries."
    )
    try:
        response = await acompletion_with_retry(
            model="vertex_ai/gemini-2.0-flash",
            messages=[
                {"role": "system", "content": _LISTING_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
        )
        data = parse_llm_json(response.choices[0].message.content)
    except Exception as exc:
        logger.warning("Faculty listing extraction failed: %s", exc)
        return []
    items = data.get("faculty") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    cleaned: list[dict] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        cleaned.append({
            "name": name,
            "profile_url": str(item.get("profile_url") or "").strip(),
            "blurb": str(item.get("blurb") or "").strip(),
        })
        if len(cleaned) >= max_faculty:
            break
    return cleaned


def _area_match_score(blurb: str, research_interests: list[str]) -> float:
    if not research_interests:
        return 0.0
    haystack = blurb.lower()
    if not haystack:
        return 0.0
    hits = sum(1 for interest in research_interests if interest.strip().lower() in haystack)
    return hits / max(1, len(research_interests))


def _pick_listing_source(sources: list[ResearchSource]) -> ResearchSource | None:
    if not sources:
        return None
    for source in sources:
        if source.source_type == "faculty_page":
            return source
    return sources[0]


async def _enrich_one(seed: dict, retrieved_at: str, sem: asyncio.Semaphore) -> FacultyDossier:
    name = seed["name"]
    async with sem:
        pubs_task = arxiv_search(name)
        nsf_task = nsf_awards_search(name)
        nih_task = nih_reporter_search(name)
        pubs, nsf_grants, nih_grants = await asyncio.gather(
            pubs_task, nsf_task, nih_task, return_exceptions=False,
        )
    return FacultyDossier(
        name=name,
        profile_url=seed.get("profile_url", ""),
        evidence_snippets=[seed["blurb"]] if seed.get("blurb") else [],
        recent_publications=pubs,
        active_grants=[*nsf_grants, *nih_grants],
        retrieved_at=retrieved_at,
        verification_status="partial" if seed.get("profile_url") else "unverified",
    )


async def enrich_faculty_dossiers(
    target: ApplicationTarget,
    sources: list[ResearchSource],
) -> list[FacultyDossier]:
    listing_source = _pick_listing_source(sources)
    if listing_source is None:
        return []

    max_faculty = int(os.getenv("STORYCOACH_FACULTY_ENRICH_MAX", "8"))
    seeds = await _extract_faculty_listing(listing_source, max_faculty=max_faculty * 2)
    if not seeds:
        return []

    if target.research_interests:
        seeds.sort(
            key=lambda s: _area_match_score(s["blurb"], target.research_interests),
            reverse=True,
        )
    seeds = seeds[:max_faculty]

    retrieved_at = datetime.now(timezone.utc).isoformat()
    sem = asyncio.Semaphore(4)
    tasks = [_enrich_one(seed, retrieved_at, sem) for seed in seeds]
    dossiers: list[FacultyDossier] = []
    for result in await asyncio.gather(*tasks, return_exceptions=True):
        if isinstance(result, FacultyDossier):
            dossiers.append(result)
        else:
            logger.warning("Per-faculty enrichment task failed: %s", result)

    if target.research_interests:
        for dossier in dossiers:
            blurb = " ".join(dossier.evidence_snippets)
            dossier.area_match_score = _area_match_score(blurb, target.research_interests)
    return dossiers
