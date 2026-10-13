"""M10-M12 save/repair step: manage core/KNOWLEDGE/screenplay_links.json.

Regenerates the owner-approved screenplay↔book pairs with the mandatory
_provenance_metadata on every record and validates the result. The original
4-field contract (screenplay_scene_id, book_chunk_id, confidence, notes) is
preserved; audit fields live under _provenance_metadata only. The save is
merge-based: owner notes and provenance metadata on disk are never lost.

Usage:
    python scripts/generate_screenplay_links.py [--out <path>]
    python scripts/generate_screenplay_links.py --repair
    python scripts/generate_screenplay_links.py --candidates [scene_000 ...]
    python scripts/generate_screenplay_links.py --approve scene_000 chunk_p_0006_... [--notes ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "core" / "CORE") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "core" / "CORE"))

from knowledge.screenplay_links_provenance import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
