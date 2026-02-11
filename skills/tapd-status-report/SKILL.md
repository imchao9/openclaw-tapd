---
name: tapd-status-report
description: 提供 TAPD OpenAPI 的基础只读接口信息，用于按项目（workspace）汇报需求、缺陷、任务、迭代状态。适用于“汇报产品研发中心状态”“给 OpenClaw 配置 TAPD 只读查询”这类请求。
homepage: https://open.tapd.cn/document/api-doc/%E6%A0%B8%E5%BF%83%E6%A6%82%E5%BF%B5/
metadata: {"openclaw":{"emoji":"📊","skillKey":"tapd-status-report","primaryEnv":"TAPD_APP_SECRET","requires":{"bins":["curl","jq","python3"],"env":["TAPD_APP_ID","TAPD_APP_SECRET","TAPD_WORKSPACE_ID"]}}}
---

# 目标

使用 TAPD OpenAPI 提供最小可用状态汇报能力：需求（Story）、缺陷（Bug）、任务（Task）、迭代（Iteration）。

# 强制只读规则（必须遵守）

本技能必须运行在**只读模式**，以下规则为硬性约束：

- 业务数据接口只能调用读取类接口（`GET`）。
- 严禁调用任何写入类业务接口：创建、修改、删除、批量更新、锁定/解锁等（如 `add_*`、`update_*`、`delete_*`、`batch_update_*`、`lock_*`、`unlock_*`）。
- 严禁对需求/缺陷/任务/迭代数据发起 `POST`、`PUT`、`PATCH`、`DELETE`。
- **唯一允许的 `POST`** 是鉴权接口 `POST /tokens/request_token`（仅用于获取 access_token，不写业务数据）。
- 如果用户提出“修改 TAPD 数据”的请求，必须拒绝执行并说明：当前技能仅支持只读查询与状态汇报。

# OpenClaw 配置约定（应用密钥模式）

要求环境变量：

- `TAPD_APP_ID`: TAPD 应用 ID（client_id）
- `TAPD_APP_SECRET`: TAPD 应用密钥（client_secret）
- `TAPD_WORKSPACE_ID`: TAPD 项目 ID（例如“产品研发中心”对应的 workspace_id）
- 可选：`TAPD_API_BASE_URL`（默认 `https://api.tapd.cn`）

推荐在 OpenClaw 的 skills 配置中注入：

```json
{
  "skills": {
    "enabled": true,
    "entries": [
      {
        "id": "tapd-status-report",
        "path": "./skills/tapd-status-report",
        "env": {
          "TAPD_APP_ID": "tapd-app-xxxxxx",
          "TAPD_WORKSPACE_ID": "your_workspace_id"
        },
        "apiKey": "your_tapd_app_secret"
      }
    ]
  }
}
```

本技能已设置 `primaryEnv: TAPD_APP_SECRET`，OpenClaw 会将 `apiKey` 自动注入该环境变量。

# 认证方式（应用 ID + 应用密钥）

基础域名：`https://api.tapd.cn`

## 1. 获取 Access Token

- `POST /tokens/request_token`
- Header: `Authorization: Basic base64(client_id:client_secret)`
- Body: `grant_type=client_credentials`

示例：

```bash
AUTH=$(printf "%s:%s" "$TAPD_APP_ID" "$TAPD_APP_SECRET" | base64)
curl -sS -X POST "https://api.tapd.cn/tokens/request_token" \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials"
```

## 2. 访问只读业务接口

Header：`Authorization: Bearer <access_token>`

# 基础只读接口（状态汇报必需）

## 1. 总量接口

- 需求总量：`GET /stories/count?workspace_id={workspace_id}`
- 缺陷总量：`GET /bugs/count?workspace_id={workspace_id}`
- 任务总量：`GET /tasks/count?workspace_id={workspace_id}`

## 2. 迭代接口

- 迭代列表：`GET /iterations?workspace_id={workspace_id}&fields=id,name,status,startdate,enddate&limit=200&page=1`

说明：

- `workspace_id` 必填。
- 单页最多 `limit=200`，超过后递增 `page` 分页拉取。
- 默认 `status=open` 可用于“当前进行中迭代”汇报。

# 内置脚本（推荐给 OpenClaw 直接调用）

脚本路径：

- `scripts/tapd_project_report_app_token.py`（应用密钥 + token）

## 推荐脚本最小用法

```bash
python3 skills/tapd-status-report/scripts/tapd_project_report_app_token.py
```

常用参数：

```bash
# 查询全部状态迭代（不过滤 status）
python3 skills/tapd-status-report/scripts/tapd_project_report_app_token.py --iteration-status ""

# 输出 JSON（便于二次加工）
python3 skills/tapd-status-report/scripts/tapd_project_report_app_token.py --format json

# 直接使用已有 token（可选）
python3 skills/tapd-status-report/scripts/tapd_project_report_app_token.py \
  --access-token "your_access_token"
```

推荐脚本入参来源：

- 优先读取命令行参数
- 否则读取环境变量：`TAPD_APP_ID`、`TAPD_APP_SECRET`、`TAPD_WORKSPACE_ID`
- 可选环境变量：`TAPD_ACCESS_TOKEN`、`TAPD_API_BASE_URL`

# 汇报输出模板

```markdown
## 产品研发中心状态汇报（YYYY-MM-DD HH:mm）

### 需求（Story）
- 总数：X

### 缺陷（Bug）
- 总数：X

### 任务（Task）
- 总数：X

### 当前迭代（open）
- #id 名称 | status=xxx | 开始 ~ 结束
```

# 可选：TAPD JS SDK 说明

你提供的包 `@opentapd/tapd-open-js-sdk` 主要用于 TAPD 嵌入应用场景（事件通信/UI/handler），不等价于直接调用 `api.tapd.cn` 的 OpenAPI SDK。

- 如果目标是“状态汇报”，优先使用本技能里的 OpenAPI 只读接口。
- 如果目标是“在 TAPD 页面内做嵌入交互”，再使用该 JS SDK。

# 官方文档入口

- OpenClaw Skills: `https://docs.openclaw.ai/tools/skills`
- TAPD 核心概念: `https://open.tapd.cn/document/api-doc/%E6%A0%B8%E5%BF%83%E6%A6%82%E5%BF%B5/`
- TAPD 使用必读: `https://open.tapd.cn/document/api-doc/API%E6%96%87%E6%A1%A3/%E4%BD%BF%E7%94%A8%E5%BF%85%E8%AF%BB.html`
- 需求数量接口: `https://open.tapd.cn/document/api-doc/API%E6%96%87%E6%A1%A3/api_reference/story/get_stories_count.html`
- 缺陷数量接口: `https://open.tapd.cn/document/api-doc/API%E6%96%87%E6%A1%A3/api_reference/bug/get_bugs_count.html`
- 任务数量接口: `https://open.tapd.cn/document/api-doc/API%E6%96%87%E6%A1%A3/api_reference/task/get_tasks_count.html`
