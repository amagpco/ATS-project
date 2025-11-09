import logging
import os
import shutil
import tempfile
from contextlib import contextmanager

from django.core.files.storage import default_storage

try:
    from docx import Document  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    Document = None

try:
    from pypdf import PdfReader  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    PdfReader = None

logger = logging.getLogger(__name__)


def _extract_pdf_text(path: str) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed")

    reader = PdfReader(path)
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_docx_text(path: str) -> str:
    if Document is None:
        raise RuntimeError("python-docx is not installed")

    document = Document(path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


@contextmanager
def _local_resume_path(resume_path: str):
    """
    Yield a local filesystem path for the given storage key.
    Downloads to a temp file when the storage backend does not expose `.path`.
    """

    temp_file = None
    try:
        try:
            local_path = default_storage.path(resume_path)
        except (NotImplementedError, AttributeError, ValueError):
            suffix = os.path.splitext(resume_path)[1] or ".tmp"
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            with default_storage.open(resume_path, "rb") as source, open(temp.name, "wb") as target:
                shutil.copyfileobj(source, target)
            temp_file = temp.name
            local_path = temp_file
        yield local_path
    finally:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)


def extract_resume_text(resume_path: str, *, settings=None) -> str:
    """
    Attempt to extract plain text from a resume file stored on disk or remote storage.

    Supports PDF, DOCX, and plain text files. Falls back to an empty string on failure.
    """

    if not resume_path:
        return ""

    if not default_storage.exists(resume_path):
        logger.warning("Resume file does not exist at %s", resume_path)
        return ""

    allow_pdf = getattr(settings, "enable_pdf_extraction", True)
    allow_docx = getattr(settings, "enable_docx_extraction", True)
    allow_text = getattr(settings, "enable_text_extraction", True)

    with _local_resume_path(resume_path) as local_path:
        ext = os.path.splitext(local_path)[1].lower()

        try:
            if ext == ".pdf":
                if not allow_pdf:
                    logger.info("PDF extraction disabled by user settings.")
                    return ""
                return _extract_pdf_text(local_path)
            if ext in (".doc", ".docx"):
                if not allow_docx:
                    logger.info("DOCX extraction disabled by user settings.")
                    return ""
                return _extract_docx_text(local_path)
            if not allow_text:
                logger.info("Plain text extraction disabled by user settings.")
                return ""
            with open(local_path, "r", encoding="utf-8", errors="ignore") as fp:
                return fp.read()
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to extract resume text: %s", exc)
            return ""


