import json
import logging
import re
from typing import Any, Dict, Optional

import cohere
from django.conf import settings

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_CHAT_MODEL",
    "CohereServiceError",
    "extract_job_posting_structured",
    "analyze_resume_with_cohere",
]

# Use a Cohere model that supports structured JSON outputs by default.
DEFAULT_CHAT_MODEL = getattr(
    settings,
    "COHERE_DEFAULT_MODEL",
    getattr(settings, "COHERE_JOB_MODEL", "command-a-03-2025"),
)
DEFAULT_TEMPERATURE = float(getattr(settings, "COHERE_DEFAULT_TEMPERATURE", 0.15))


class CohereServiceError(Exception):
    """Raised when Cohere integration fails."""


def _get_cohere_client() -> cohere.Client:
    api_key = "LhlAO6RSLOGBEJsTMI5wcR2YAvT8wkZ93DJ5luEN"
    if not api_key:
        raise CohereServiceError(
            "Cohere API key is not configured. Set COHERE_API_KEY in settings."
        )

    try:
        return cohere.Client(api_key=api_key)
    except Exception as exc:  # pragma: no cover - defensive
        raise CohereServiceError("Unable to initialise Cohere client.") from exc


def _extract_json_block(text: str) -> str:
    """
    Remove any prose or markdown fences wrapped around the JSON payload.
    """

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    match = re.search(r"(\{.*\})", text, re.DOTALL)
    return match.group(1) if match else text


def _generate_structured_output(
    *,
    prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Shared helper that calls Cohere and parses a JSON object from the response.

    Structured outputs are enforced using response_format={"type": "json_object"}
    as outlined in Cohere's release notes on structured outputs [1].

    [1]: https://docs.cohere.com/changelog/structured-outputs-tools
    """

    client = _get_cohere_client()
    selected_model = model or DEFAULT_CHAT_MODEL
    selected_temp = temperature if temperature is not None else DEFAULT_TEMPERATURE

    try:
        response = client.chat(
            model=selected_model,
            message=prompt,
            temperature=selected_temp,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # pragma: no cover - API failure handling
        logger.exception("Cohere chat API call failed: %s", exc)
        raise CohereServiceError("Cohere API request failed.") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise CohereServiceError("Cohere response did not include any text content.")

    cleaned = _extract_json_block(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Cohere response was not valid JSON: %s", raw_text)
        raise CohereServiceError("Failed to parse Cohere JSON response.") from exc

    data.setdefault("model_used", selected_model)
    data.setdefault("temperature_used", selected_temp)
    return data


def extract_job_posting_structured(
    job_text: str,
    *,
    job_url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    extra_instructions: str = "",
) -> Dict[str, Any]:
    """
    Uses Cohere to transform raw job posting text into a structured JSON payload.
    """

    if not job_text or not job_text.strip():
        raise CohereServiceError("No job posting content provided for analysis.")

    system_prompt = (
        "You are an expert HR analyst that extracts structured data from job postings. "
        "Return a compact JSON object with keys: title, department, location, summary, "
        "description, responsibilities (list), requirements (list), skills (list), "
        "employment_type, seniority. Description should be concise (under 1200 chars). "
        "Keep lists to a maximum of 6 items each."
    )

    prompt_parts = [
        system_prompt,
        "",
        f"Job source URL: {job_url or 'unknown'}",
        "Job posting content:",
        job_text.strip(),
    ]

    if extra_instructions.strip():
        prompt_parts.insert(
            1,
            f"Additional instructions: {extra_instructions.strip()}",
        )

    prompt = "\n".join(prompt_parts)

    structured = _generate_structured_output(
        prompt=prompt,
        model=model,
        temperature=temperature,
    )

    structured.setdefault("title", "")
    structured.setdefault("department", "")
    structured.setdefault("location", "")
    structured.setdefault("summary", "")
    structured.setdefault("description", "")
    structured.setdefault("responsibilities", [])
    structured.setdefault("requirements", [])
    structured.setdefault("skills", [])
    structured.setdefault("employment_type", "")
    structured.setdefault("seniority", "")

    return structured


def analyze_resume_with_cohere(
    resume_text: str,
    job_description: str,
    *,
    job_title: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    extra_instructions: str = "",
    improvements_target: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Ask Cohere to evaluate a resume against a job description and return structured data.
    """

    if not resume_text or not resume_text.strip():
        raise CohereServiceError("Resume text is empty; cannot analyse candidate profile.")

    if not job_description or not job_description.strip():
        raise CohereServiceError("Job description is missing; cannot perform matching.")

    system_prompt = (
        "You are an applicant tracking assistant. Compare the candidate resume with the job "
        "description and return a JSON object with the following keys:\n"
        "- match_score: float between 0 and 1 representing the fit.\n"
        "- summary: concise paragraph (<= 120 words) summarising the candidate.\n"
        "- improvements: list of 3-6 concrete suggestions the candidate could do to improve.\n"
        "- recommended_skills: list of additional skills/keywords worth highlighting.\n"
        "All textual content should be plain text (no markdown)."
    )

    prompt_parts = [
        system_prompt,
        "",
        f"Job title: {job_title or 'Unknown'}",
        "Job description:",
        job_description.strip(),
        "",
        "Resume text:",
        resume_text.strip(),
    ]

    if extra_instructions.strip():
        prompt_parts.insert(
            1,
            f"Additional instructions: {extra_instructions.strip()}",
        )

    prompt = "\n".join(prompt_parts)

    structured = _generate_structured_output(
        prompt=prompt,
        model=model,
        temperature=temperature,
    )

    structured.setdefault("match_score", 0)
    structured.setdefault("summary", "")
    structured.setdefault("improvements", [])
    structured.setdefault("recommended_skills", [])

    try:
        structured["match_score"] = float(structured["match_score"])
    except (TypeError, ValueError):
        structured["match_score"] = 0.0

    if not isinstance(structured["improvements"], list):
        structured["improvements"] = (
            [structured["improvements"]] if structured["improvements"] else []
        )

    if not isinstance(structured["recommended_skills"], list):
        structured["recommended_skills"] = (
            [structured["recommended_skills"]] if structured["recommended_skills"] else []
        )

    if (
        improvements_target is not None
        and improvements_target >= 0
        and isinstance(structured["improvements"], list)
    ):
        structured["improvements"] = structured["improvements"][:improvements_target]

    return structured

