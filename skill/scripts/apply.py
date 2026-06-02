#!/usr/bin/env python3
"""Monkey-patch FeishuAdapter to support markdown tables via CardKit v2.

Apply this patch once before starting the gateway; it is idempotent.

Usage:
    python3 apply.py                     # apply the patch
    python3 apply.py --check             # check if patch is needed
    python3 apply.py --force             # re-apply even if already patched
"""

import json
import logging
import os
import re
import sys

# Ensure the Hermes source tree is on sys.path so 'from gateway.platforms.feishu'
# resolves regardless of whether we're running in a bare venv, an editable
# install, or a container.
_HERMES_HOME = os.environ.get(
    "HERMES_HOME",
    os.path.expanduser("~/.hermes"),
)
_CANDIDATES = [
    os.path.join(_HERMES_HOME, "hermes-agent"),
    "/opt/hermes",
]
for _p in _CANDIDATES:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from typing import Any, Dict, List

logger = logging.getLogger("feishu-table-fix")

# ---------------------------------------------------------------------------
# Core table detection and CardKit v2 builder
# These are self-contained so the patch works on stock Hermes (no assumptions
# about what's already in feishu.py).
# ---------------------------------------------------------------------------

_MARKDOWN_TABLE_RE = re.compile(r"^\|.*\|\n\|[-|: ]+\|", re.MULTILINE)


def _build_table_card_payload(content: str) -> str:
    """Build a Feishu CardKit v2 card with a native table component."""
    lines = content.splitlines()
    non_table_lines: List[str] = []
    table_start = -1
    table_end = -1
    in_table = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not in_table:
            if stripped.startswith("|") and stripped.endswith("|"):
                if i + 1 < len(lines) and re.match(r"^\|[-|: ]+\|$", lines[i + 1].strip()):
                    table_start = i
                    in_table = True
                    continue
            non_table_lines.append(line)
        else:
            if stripped.startswith("|") and stripped.endswith("|"):
                table_end = i
            else:
                in_table = False
                non_table_lines.append(line)

    def _parse_table_row(row_line: str) -> List[str]:
        return [c.strip() for c in row_line.split("|") if c.strip()]

    table_headers: List[str] = []
    table_rows: List[List[str]] = []
    if table_start >= 0 and table_end >= 0:
        table_headers = _parse_table_row(lines[table_start])
        for row_idx in range(table_start + 2, table_end + 1):
            row_cells = _parse_table_row(lines[row_idx])
            if row_cells:
                table_rows.append(row_cells)

    elements: List[Dict[str, Any]] = []

    if non_table_lines:
        intro_text = "\n".join(non_table_lines).strip()
        if intro_text:
            elements.append({"tag": "markdown", "content": intro_text})

    if table_headers:
        columns = [
            {
                "name": f"col_{idx}",
                "display_name": hdr.replace("**", "").replace("__", "").strip(),
                "data_type": "text",
                "width": "auto",
            }
            for idx, hdr in enumerate(table_headers)
        ]

        rows_data = []
        for row in table_rows:
            row_dict = {}
            for idx, cell in enumerate(row):
                row_dict[f"col_{idx}"] = cell.replace("**", "").replace("__", "").strip()
            rows_data.append(row_dict)

        elements.append({
            "tag": "table",
            "columns": columns,
            "rows": rows_data,
            "header_style": {
                "bold": True,
                "text_align": "left",
                "text_size": "normal",
                "background_style": "none",
                "text_color": "default",
                "lines": 1,
            },
        })

    card = {
        "schema": "2.0",
        "config": {"wide_screen_mode": True},
        "body": {"elements": elements},
    }
    return json.dumps(card, ensure_ascii=False)


# Sentinel to detect if we've already patched
_HAS_TABLE_FIX = False


def apply_patch(force: bool = False) -> bool:
    """Monkey-patch FeishuAdapter._build_outbound_payload.

    Returns True if the patch was applied (or already applied), False on error.
    """
    global _HAS_TABLE_FIX

    if _HAS_TABLE_FIX and not force:
        logger.info("feishu-table-fix: already patched, skipping")
        return True

    try:
        from gateway.platforms.feishu import FeishuAdapter
    except ImportError as exc:
        logger.error("feishu-table-fix: cannot import FeishuAdapter: %s", exc)
        return False

    original = getattr(FeishuAdapter, "_build_outbound_payload", None)
    if original is None:
        logger.error("feishu-table-fix: FeishuAdapter._build_outbound_payload not found")
        return False

    # If original already calls _build_table_card_payload, no need to patch
    if not force:
        import inspect
        try:
            src = inspect.getsource(original)
            if "_build_table_card_payload" in src or "_build_table_card" in src:
                logger.info(
                    "feishu-table-fix: _build_outbound_payload already references "
                    "table-card builder, patch is unnecessary"
                )
                _HAS_TABLE_FIX = True
                return True
        except (OSError, TypeError):
            pass  # can't inspect, apply anyway

    def patched_build(self, content: str):
        if _MARKDOWN_TABLE_RE.search(content):
            return ("interactive", _build_table_card_payload(content))
        return original(self, content)

    FeishuAdapter._build_outbound_payload = patched_build
    _HAS_TABLE_FIX = True
    logger.info("feishu-table-fix: patch applied successfully")
    return True


def check_needed() -> bool:
    """Check whether the patch is needed."""
    try:
        from gateway.platforms.feishu import FeishuAdapter
        import inspect
        src = inspect.getsource(FeishuAdapter._build_outbound_payload)
        if "_build_table_card_payload" in src or "_build_table_card" in src:
            print("✅ 已修复: _build_outbound_payload 已包含表格处理逻辑")
            return False
    except Exception:
        pass
    print("⚠️  需要修复: _build_outbound_payload 未检测表格，markdown 表格将渲染为空白")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if "--check" in sys.argv:
        check_needed()
    else:
        force = "--force" in sys.argv
        success = apply_patch(force=force)
        sys.exit(0 if success else 1)
