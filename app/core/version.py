"""
Source unique de la version applicative — lecture du fichier VERSION racine.

POURQUOI ce module : SPEC_ci-cd.md D-CI-5 impose une source unique lisible par
la CI (job publish), le watcher prod et l'UI de supervision. Le format est le
versionning Adrian MAJOR.MINOR.BUILD, regex stricte — tout écart est une
erreur explicite, jamais un fallback silencieux.
"""
from __future__ import annotations

import re
from pathlib import Path

# Strict MAJOR.MINOR.BUILD — same regex as the CI publish job (CI-4.1).
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

# app/core/version.py -> parents[2] == project root (where VERSION lives).
DEFAULT_VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"


def read_version(path: str | Path | None = None) -> str:
    """Return the version string from the root ``VERSION`` file.

    ``path`` overrides the default root file (tests, tooling).
    Raises ``FileNotFoundError`` if the file is absent, ``ValueError`` if the
    content is not a strict ``MAJOR.MINOR.BUILD`` version.
    """
    version_file = Path(path) if path is not None else DEFAULT_VERSION_FILE
    raw = version_file.read_text(encoding="utf-8").strip()
    if not _VERSION_RE.match(raw):
        raise ValueError(
            f"invalid VERSION content: {raw!r} (expected MAJOR.MINOR.BUILD)"
        )
    return raw
