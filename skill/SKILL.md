---
name: feishu-table-fix
description: "Fix Feishu markdown table rendering — converts pipe-table syntax to CardKit v2 native table components so tables display correctly instead of appearing blank."
version: 1.1.0
metadata:
  hermes:
    tags: [feishu, card, table, cardkit, gateway, fix]
    related_skills: [feishu-card-table-render, hermes-s6-container-supervision]
---

# Feishu Markdown Table Fix

## Problem

飞书的 `post` 消息类型和旧格式卡片的 `tag: "markdown"` 元素**不支持 GFM pipe-table 语法**。
Hermes 发送 markdown 表格时，表格区域会渲染为**空白**。

```
| 列 A | 列 B |          →      (飞书上显示为空白)
|------|------|
| 数据1 | 数据2 |
```

## Solution

Monkey-patch `FeishuAdapter._build_outbound_payload`，检测到表格内容时自动转为 **CardKit v2 原生 table 组件**。

## Architecture

```
Markdown Message
    │
    ▼
FeishuAdapter._build_outbound_payload()
    │
    ├─ Has pipe-table? ──Yes──► _build_table_card_payload() → CardKit v2
    │                                │
    │                            tag: "table"
    │                            columns: [...]
    │                            rows: [...]
    │
    └─ No ──► Original handler (text/post/message_card)
```

## Quick Start

```bash
# 1. Check if patch is needed
python3 skill/scripts/apply.py --check

# 2. Apply patch (idempotent)
python3 skill/scripts/apply.py

# 3. Restart gateway
hermes gateway restart
```

## Deployment

### 本地部署

```bash
hermes skills install <this-repo-url>
python3 ~/.hermes/skills/feishu-table-fix/scripts/apply.py
hermes gateway restart
```

### Docker 容器部署

#### 共享 skill 挂载（推荐）

```bash
# 宿主机
mkdir -p /opt/hermes-docker/shared-skills/feishu/feishu-table-fix
cp -r skill/* /opt/hermes-docker/shared-skills/feishu/feishu-table-fix/

# 容器启动
docker run ... \
  -v /opt/hermes-docker/shared-skills:/opt/shared-skills:ro

# 合并 + 打补丁
docker exec <container> sh -c '
  cp -rn /opt/shared-skills/* /opt/data/skills/
  python3 /opt/data/skills/feishu/feishu-table-fix/scripts/apply.py
'
```

#### 单文件挂载

```bash
docker run ... \
  -v ./scripts/apply.py:/opt/apply.py:ro
docker exec <container> python3 /opt/apply.py
```

#### 自定义镜像

```Dockerfile
FROM hermes-agent:latest
COPY scripts/apply.py /opt/hermes/
RUN echo 'python3 /opt/hermes/apply.py' >> /etc/s6-overlay/s6-rc.d/cont-init.d/03-feishu-table-fix
```

## Compatibility

| Aspect | Detail |
|--------|--------|
| Hermes 版本 | ≥ v2.0 (`FeishuAdapter._build_outbound_payload`) |
| 依赖 | 零外部依赖，完全自包含 |
| 幂等性 | 多次执行安全，不会重复打补丁 |
| 自动跳过 | 检测到已有修复时跳过 |

## Verification

在飞书上给 Bot 发送表格消息：

```
| 测试列1 | 测试列2 |
|---------|---------|
| 值 A    | 值 B    |
```

Bot 回复应显示正常表格，而非空白。

## Related Skills

- `feishu-card-table-render` — CardKit v2 表格格式参考、调试经验、两种发送路径说明
- `hermes-s6-container-supervision` — 多容器部署指南
