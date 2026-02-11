# tapd-status-report

基于 TAPD OpenAPI 的只读状态汇报脚本，支持两种鉴权方式：

- 基础账号鉴权：`scripts/tapd_project_report.py`
- 应用密钥鉴权（推荐）：`scripts/tapd_project_report_app_token.py`

## 环境变量

### 通用可选

- `TAPD_API_BASE_URL`：API 基础地址，默认 `https://api.tapd.cn`

### 方式一：基础账号鉴权（tapd_project_report.py）

必填：

- `TAPD_API_USER`
- `TAPD_API_PASSWORD`
- `TAPD_WORKSPACE_ID`

### 方式二：应用密钥鉴权（tapd_project_report_app_token.py，推荐）

必填（二选一）：

- 方案 A：`TAPD_ACCESS_TOKEN` + `TAPD_WORKSPACE_ID`
- 方案 B：`TAPD_APP_ID` + `TAPD_APP_SECRET` + `TAPD_WORKSPACE_ID`

可选：

- `TAPD_ACCESS_TOKEN`（有现成 token 时可直接使用）

## 快速开始

```bash
# 基础账号鉴权
export TAPD_API_USER="your_user"
export TAPD_API_PASSWORD="your_password"
export TAPD_WORKSPACE_ID="your_workspace_id"
python3 scripts/tapd_project_report.py
```

```bash
# 应用密钥鉴权（推荐）
export TAPD_APP_ID="your_app_id"
export TAPD_APP_SECRET="your_app_secret"
export TAPD_WORKSPACE_ID="your_workspace_id"
python3 scripts/tapd_project_report_app_token.py
```

```bash
# 输出 JSON
python3 scripts/tapd_project_report_app_token.py --format json
```
