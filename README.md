# Hermes Feishu Table Fix

> 🛠️ Make Markdown tables render properly in Feishu (飞书) — converts pipe-table syntax to CardKit v2 native table components.

[![GitHub](https://img.shields.io/badge/Hermes-Agent-blueviolet)](https://github.com/NousResearch/hermes-agent)
[![Feishu](https://img.shields.io/badge/Feishu-CardKit-blue)](https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-platform/cardkit/overview)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## The Problem

Feishu's `post` message type and the `tag: "markdown"` element in legacy cards **do not support GFM pipe-table syntax**. When Hermes Agent sends markdown tables to Feishu, the table renders as **a blank area**:

```
| Column A | Column B |     →     (blank in Feishu)
|----------|----------|
| Data 1   | Data 2   |
```

## The Solution

Monkey-patches `FeishuAdapter._build_outbound_payload` to detect pipe-table content and automatically convert it to **CardKit v2 native `tag: "table"` components**, which Feishu renders correctly.

## Quick Start

```bash
# Check if patch is needed
python3 skill/scripts/apply.py --check

# Apply the patch (idempotent)
python3 skill/scripts/apply.py

# Restart Hermes Gateway
hermes gateway restart
```

Now tables will render correctly in all Feishu messages.

## How It Works

1. **Detection** — Regex scans outbound message content for pipe-table patterns
2. **Conversion** — Parses table rows/columns and builds a CardKit v2 table payload
3. **Delivery** — Sends as `interactive` (card) instead of `text`/`post`

```python
# Simplified logic
def patched_build(self, content):
    if _MARKDOWN_TABLE_RE.search(content):
        return "interactive", _build_table_card_payload(content)
    return original_build(self, content)
```

## Docker Deployment

### Option 1: Shared Skill Mount (Recommended)

```bash
# On host
mkdir -p /opt/hermes-docker/shared-skills/feishu/feishu-table-fix
cp -r skill/* /opt/hermes-docker/shared-skills/feishu/feishu-table-fix/

# In container startup
docker run ... -v /opt/hermes-docker/shared-skills:/opt/shared-skills:ro

# Apply patch
docker exec <container> python3 /opt/shared-skills/feishu/feishu-table-fix/scripts/apply.py
```

### Option 2: Single-File Mount

```bash
docker run ... -v ./scripts/apply.py:/opt/apply.py:ro
docker exec <container> python3 /opt/apply.py
```

## Compatibility

- **Hermes Agent**: ≥ v2.0 (any version with `FeishuAdapter._build_outbound_payload`)
- **Self-contained**: Zero external dependencies
- **Idempotent**: Safe to run multiple times
- **Autoskip**: Detects existing patches and skips re-application

## Verification

Send this message to your Feishu Bot:

```
| Test Col 1 | Test Col 2 |
|------------|------------|
| Value A    | Value B    |
```

The bot's reply should show a properly rendered table, not a blank area.

---

## Related

- [`feishu-card-table-render`] — CardKit v2 format reference and debugging notes
- [`hermes-s6-container-supervision`] — Multi-container deployment guide
