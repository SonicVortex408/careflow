"""Shared input validation for anything that becomes a filesystem path.

`patient_id` and uploaded filenames are both attacker-controlled strings
that get joined into paths under `patient_documents/` and `patient_faiss/`
(see app/api/documents.py, app/retrieval/patient_ingest.py). Neither was
validated before the join, which is a path-traversal surface: a
`patient_id` of `"../../etc"` or a filename of `"../../../x.pdf"` would
escape the intended directory. Every path-building call site must go
through these two functions first.
"""

import re
from pathlib import PurePosixPath

# Mongo ObjectId: exactly 24 hex characters. patient_id in this system is
# always a Mongo _id string (see ARCHITECTURE.md decision 3), so this is
# not an arbitrary format choice -- it's the actual shape of the value.
_OBJECT_ID_RE = re.compile(r"^[0-9a-fA-F]{24}$")

# Conservative allowlist for the parts of a filename we keep: letters,
# digits, dot, dash, underscore, space. Anything else (path separators,
# null bytes, unicode tricks) is stripped.
_SAFE_FILENAME_CHARS_RE = re.compile(r"[^A-Za-z0-9._\- ]+")


class InvalidPatientId(ValueError):
    pass


class InvalidFilename(ValueError):
    pass


def validate_patient_id(patient_id: str) -> str:
    """
    Validate that patient_id is a 24-hex-character Mongo ObjectId.

    Raises InvalidPatientId otherwise. Never returns a value that has not
    been checked against the allowlist regex -- there is no "best effort"
    path here.
    """

    if not isinstance(patient_id, str) or not _OBJECT_ID_RE.match(patient_id):
        raise InvalidPatientId(
            f"patient_id must be a 24-character hex ObjectId, got: {patient_id!r}"
        )

    return patient_id


def safe_filename(filename: str) -> str:
    """
    Reduce an uploaded filename to a safe basename before it is joined
    into any path.

    - Takes only the final path component (defeats `../../x` and
      absolute paths, on both POSIX and Windows separators).
    - Strips characters outside the safe allowlist.
    - Falls back to a fixed name if nothing usable remains, rather than
      ever returning an empty string that could resolve to a directory.
    """

    if not filename:
        raise InvalidFilename("filename is required")

    # Strip any directory components from either separator style.
    basename = filename.replace("\\", "/")
    basename = PurePosixPath(basename).name

    cleaned = _SAFE_FILENAME_CHARS_RE.sub("_", basename).strip()
    cleaned = cleaned.lstrip(".")  # no dotfiles, no bare ".."

    if not cleaned:
        cleaned = "upload"

    # Keep filenames bounded -- some filesystems choke past ~255 bytes.
    # Truncate the stem, not the extension, so a long filename doesn't
    # silently lose the .pdf/.txt suffix that downstream MIME/type
    # checks rely on.
    if len(cleaned) > 200:
        stem, dot, ext = cleaned.rpartition(".")
        if dot and 0 < len(ext) <= 10:
            cleaned = stem[: 200 - len(ext) - 1] + dot + ext
        else:
            cleaned = cleaned[:200]

    return cleaned
