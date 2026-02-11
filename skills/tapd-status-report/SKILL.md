---
name: tapd-status-report
description: 提供 TAPD OpenAPI 的基础接口信息，用于按项目（workspace）汇报需求、缺陷、任务状态。适用于“汇报产品研发中心需求状态/缺陷状态/任务状态”“给 OpenClaw 配置 TAPD 状态查询”这类请求。
homepage: https://open.tapd.cn/document/api-doc/%E6%A0%B8%E5%BF%83%E6%A6%82%E5%BF%B5/
metadata: {"openclaw":{"emoji":"📊","skillKey":"tapd-status-report","primaryEnv":"TAPD_API_PASSWORD","requires":{"bins":["curl","jq","python3"],"env":["TAPD_API_USER","TAPD_API_PASSWORD","TAPD_WORKSPACE_ID"]}}}
---

# 目标

使用 TAPD OpenAPI 提供最小可用状态汇报能力：需求（story）、缺陷（bug）、任务（task）。

# 强制只读规则（必须遵守）

本技能必须运行在**只读模式**，以下规则为硬性约束：

- 只能调用读取接口（`GET`），不能调用任何写入类接口。
- 严禁使用 `POST`、`PUT`、`PATCH`、`DELETE` 请求方法。
- 严禁调用任何创建、修改、删除、批量更新、锁定/解锁等操作接口（如 `add_*`、`update_*`、`delete_*`、`batch_update_*`、`lock_*`、`unlock_*`）。
- 如果用户提出“修改 TAPD 数据”的请求，必须拒绝执行并说明：当前技能仅支持只读查询与状态汇报。

# OpenClaw 配置约定

要求环境变量：

- `TAPD_API_USER`: TAPD API user
- `TAPD_API_PASSWORD`: TAPD API password
- `TAPD_WORKSPACE_ID`: TAPD 项目 ID（例如“产品研发中心”对应的 workspace_id）

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
          "TAPD_API_USER": "your_api_user",
          "TAPD_WORKSPACE_ID": "your_workspace_id"
        },
        "apiKey": "your_api_password"
      }
    ]
  }
}
```

本技能已设置 `primaryEnv: TAPD_API_PASSWORD`，OpenClaw 会将 `apiKey` 自动注入该环境变量。

# 基础接口（状态汇报必需）

认证方式：HTTP Basic Auth（`api_user:api_password`）

基础域名：`https://api.tapd.cn`

## 1. 总量接口（推荐优先使用）

- 需求总量：`GET /stories/count?workspace_id={workspace_id}`
- 缺陷总量：`GET /bugs/count?workspace_id={workspace_id}`
- 任务总量：`GET /tasks/count?workspace_id={workspace_id}`

最小示例：

```bash
curl -sS -u "$TAPD_API_USER:$TAPD_API_PASSWORD" \
  "https://api.tapd.cn/stories/count?workspace_id=$TAPD_WORKSPACE_ID"
```

返回结构（关键字段）：

- `status`: `1` 表示调用成功
- `data.count`: 数量值
- `info`: `"success"` 代表成功

## 2. 状态明细接口（用于状态分布）

- 需求列表：`GET /stories?workspace_id={workspace_id}&fields=id,name,status&limit=200&page=1`
- 缺陷列表：`GET /bugs?workspace_id={workspace_id}&fields=id,title,status&limit=200&page=1`
- 任务列表：`GET /tasks?workspace_id={workspace_id}&fields=id,name,status&limit=200&page=1`

说明：

- `workspace_id` 必填。
- 单页最多 `limit=200`，超过后递增 `page` 分页拉取。
- 汇报状态分布时，统计每条记录的 `status` 字段频次。

## 3. 状态枚举获取接口（避免硬编码状态值）

- 需求字段定义：`GET /stories/get_fields_info?workspace_id={workspace_id}`
- 缺陷字段定义：`GET /bugs/get_fields_info?workspace_id={workspace_id}`
- 任务字段定义：`GET /tasks/get_fields_info?workspace_id={workspace_id}`

说明：

- TAPD 项目可能自定义状态流转，状态值不要写死。
- 先查字段定义，再按返回的 `status` 候选值做分组统计更稳妥。

# 内置脚本（推荐给 OpenClaw 直接调用）

脚本路径：

- `scripts/tapd_project_report.py`

用途：

- 输出当前项目需求/缺陷/任务总数
- 输出当前进行中的迭代列表（默认 `status=open`）

最小用法：

```bash
python3 skills/tapd-status-report/scripts/tapd_project_report.py
```

常用参数：

```bash
# 查询全部状态迭代（不过滤 status）
python3 skills/tapd-status-report/scripts/tapd_project_report.py --iteration-status ""

# 输出 JSON（便于二次加工）
python3 skills/tapd-status-report/scripts/tapd_project_report.py --format json
```

脚本入参来源：

- 优先读取命令行参数
- 否则读取环境变量：`TAPD_API_USER`、`TAPD_API_PASSWORD`、`TAPD_WORKSPACE_ID`

# 汇报输出模板

按以下结构输出状态汇报：

```markdown
## 产品研发中心状态汇报（YYYY-MM-DD HH:mm）

### 需求（Story）
- 总数：X
- 状态分布：status_a: n, status_b: n, ...

### 缺陷（Bug）
- 总数：X
- 状态分布：status_a: n, status_b: n, ...

### 任务（Task）
- 总数：X
- 状态分布：status_a: n, status_b: n, ...
```

# 可选：TAPD JS SDK 说明

你提供的包 `@opentapd/tapd-open-js-sdk` 可用于 TAPD 嵌入应用场景（事件通信/UI/handler），不等价于直接调用 `api.tapd.cn` 的 OpenAPI SDK。

- 如果目标是“状态汇报”，优先使用本技能里的 OpenAPI 接口。
- 如果目标是“在 TAPD 页面内做嵌入交互”，再使用该 JS SDK。

# 官方文档入口

- OpenClaw Skills: `https://docs.openclaw.ai/tools/skills`
- TAPD 核心概念: `https://open.tapd.cn/document/api-doc/%E6%A0%B8%E5%BF%83%E6%A6%82%E5%BF%B5/`
- 需求数量接口: `https://open.tapd.cn/document/api-doc/API%E6%96%87%E6%A1%A3/api_reference/story/get_stories_count.html`
- 缺陷数量接口: `https://open.tapd.cn/document/api-doc/API%E6%96%87%E6%A1%A3/api_reference/bug/get_bugs_count.html`
- 任务数量接口: `https://open.tapd.cn/document/api-doc/API%E6%96%87%E6%A1%A3/api_reference/task/get_tasks_count.html`
