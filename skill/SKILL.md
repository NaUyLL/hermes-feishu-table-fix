---
name: feishu-table-fix
description: "Fix Feishu markdown table rendering — converts pipe-table syntax to CardKit v2 native table components so tables display correctly instead of appearing blank."
version: 1.0.0
metadata:
  hermes:
    tags: [feishu, card, table, cardkit, gateway, fix]
    related_skills: [feishu-card-table-render]
---

# Feishu Markdown Table Fix

## Problem

Feishu 的 `post` 消息类型和旧格式卡片的 `tag: "markdown"` 元素**不支持 GFM pipe-table 语法**。
当你通过 Hermes 在飞书上发送 markdown 表格时，表格区域会渲染为**空白**。

```
| 列 A | 列 B |          →      (飞书上显示为空白)
|------|------|
| 数据1 | 数据2 |
```

## Solution

Monkey-patch `FeishuAdapter._build_outbound_payload`，检测到表格内容时自动转为 **CardKit v2 原生 table 组件**。

## Quick Start

```bash
# 1. 安装 skill
hermes skills install <this-skill-url>

# 2. 检查是否需要修复
python3 ~/.hermes/skills/feishu-table-fix/scripts/apply.py --check

# 3. 应用补丁
python3 ~/.hermes/skills/feishu-table-fix/scripts/apply.py

# 4. 重启 gateway
hermes gateway restart
```

## Docker 容器部署

### 共享 skill 挂载（推荐）

将 skill 放入共享目录，容器以只读挂载，启动后 `cp -rn` 合并到私有 skills：

```bash
# 宿主机
mkdir -p /opt/hermes-docker/shared-skills/feishu/feishu-table-fix
cp -r ~/.hermes/skills/feishu/feishu-table-fix/* \
      /opt/hermes-docker/shared-skills/feishu/feishu-table-fix/

# 启动容器
docker run ... \
  -v /opt/hermes-docker/shared-skills:/opt/shared-skills:ro

# 合并 + 打补丁
docker exec <container> sh -c '
  cp -rn /opt/shared-skills/* /opt/data/skills/
  python3 /opt/data/skills/feishu/feishu-table-fix/scripts/apply.py
'
```

### 单文件挂载

```bash
docker run ... \
  -v ~/.hermes/skills/feishu/feishu-table-fix/scripts/apply.py:/opt/apply.py:ro
docker exec <container> python3 /opt/apply.py
```

### 构建自定义镜像

```Dockerfile
FROM hermes-agent:latest
COPY feishu-table-fix/scripts/apply.py /opt/hermes/
RUN echo 'python3 /opt/hermes/apply.py' >> /etc/s6-overlay/s6-rc.d/cont-init.d/03-feishu-table-fix
```

更多多容器部署细节见 `hermes-s6-container-supervision` skill 的 `references/multi-container-deployment.md`。

## How It Works

```python
# Monkey-patch FeishuAdapter._build_outbound_payload
def patched_build(self, content):
    if _MARKDOWN_TABLE_RE.search(content):
        return "interactive", _build_table_card_payload(content)
    return original_build(self, content)
```

`_build_table_card_payload` 解析 markdown 内容中的 pipe-table → CardKit v2 `tag: "table"` 原生组件 → 飞书客户端正常渲染表格。

## Verification

在飞书上给 Bot 发送一条表格消息：

```
| 测试列1 | 测试列2 |
|---------|---------|
| 值 A    | 值 B    |
```

Bot 回复中应显示正常渲染的表格，而非空白。

## Compatibility

- Hermes Agent >= v2.0 (any version with `FeishuAdapter._build_outbound_payload`)
- 完全自包含，不依赖 feishu.py 的特定版本
- 幂等：重复执行不会重复打补丁
- 检测到已有修复时自动跳过

## Related

- `feishu-card-table-render`: CardKit v2 表格格式参考、调试经验、两种发送路径说明
