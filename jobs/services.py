import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup
from django.utils.text import Truncator

from analyzer.services import CohereServiceError, extract_job_posting_structured
from .models import JobPosition

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
)


class JobImportError(Exception):
    """Raised when importing an external job profile fails."""


@dataclass
class JobImportResult:
    job: JobPosition
    structured: Dict[str, Any]
    raw_text: str


def _fetch_remote_page(url: str) -> str:
    try:
        response = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.exception("Failed to fetch remote job profile: %s", exc)
        raise JobImportError("Unable to fetch the job profile URL.") from exc

    # Guard against very large pages
    return response.text[:500_000]


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = " ".join(soup.stripped_strings)
    return Truncator(text).chars(10_000)


def _compose_description(structured: Dict[str, Any], fallback_text: str) -> str:
    blocks: list[str] = []

    summary = structured.get("summary")
    if summary:
        blocks.append(summary.strip())

    description = structured.get("description")
    if description:
        blocks.append(description.strip())

    responsibilities = structured.get("responsibilities") or []
    if responsibilities:
        blocks.append(
            "Key Responsibilities:\n- " + "\n- ".join(responsibilities[:10])
        )

    requirements = structured.get("requirements") or []
    if requirements:
        blocks.append("Requirements:\n- " + "\n- ".join(requirements[:10]))

    skills = structured.get("skills") or []
    if skills:
        blocks.append("Preferred Skills:\n- " + "\n- ".join(skills[:10]))

    if not blocks:
        blocks.append(fallback_text)

    return "\n\n".join(blocks)


def import_job_from_url(url: str, *, created_by, user_settings=None) -> JobImportResult:
    if not url:
        raise JobImportError("A job profile URL is required.")

    html = _fetch_remote_page(url)
    plain_text = _html_to_text(html)

    if user_settings is None:
        user_settings = created_by.get_ai_settings()

    job_model = getattr(user_settings, "job_analysis_model", None)
    job_temperature = getattr(user_settings, "job_temperature", None)
    job_prompt_extra = getattr(user_settings, "job_additional_prompt", "")

    try:
        structured = extract_job_posting_structured(
            plain_text,
            job_url=url,
            model=job_model,
            temperature=float(job_temperature) if job_temperature is not None else None,
            extra_instructions=job_prompt_extra,
        )
    except CohereServiceError as exc:
        raise JobImportError(str(exc)) from exc

    title = structured.get("title") or "Imported Job"
    department = structured.get("department", "")
    description = _compose_description(structured, plain_text)

    job, created = JobPosition.objects.update_or_create(
        source_url=url,
        defaults={
            "title": title.strip(),
            "description": description.strip(),
            "department": department.strip()[:120],
            "created_by": created_by,
        },
    )

    if not created:
        logger.info("Updated existing job position from source URL %s", url)

    return JobImportResult(job=job, structured=structured, raw_text=plain_text)

