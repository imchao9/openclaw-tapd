# OpenClaw TAPD Status Plugin

这是一个用于 OpenClaw 的插件仓库，提供 TAPD 需求/缺陷/任务/迭代状态汇报技能：

- 插件 ID：`tapd-status-report`
- Skill 路径：`skills/tapd-status-report/SKILL.md`

## 安装（Git 仓库）

```bash
openclaw plugins install git@github.com:imchao9/openclaw-tapd.git
```

或：

```bash
openclaw plugins install https://github.com/imchao9/openclaw-tapd.git
```

## 本地联调

```bash
openclaw plugins install -l .
```

## 目录结构

```text
.
├── index.js
├── openclaw.plugin.json
├── package.json
└── skills
    └── tapd-status-report
        ├── SKILL.md
        └── scripts
            ├── tapd_project_report.py
            └── tapd_project_report_app_token.py
```

## 推荐认证方式

- 推荐使用“应用 ID + 应用密钥”换取 token（`client_credentials`）。
- 推荐脚本：`skills/tapd-status-report/scripts/tapd_project_report_app_token.py`
- 严格只读：业务接口只调用 `GET`，不调用任何写入类接口。

## 安全说明

- 仓库不包含真实 TAPD 密钥、密码、Token。
- 运行时请通过环境变量或 OpenClaw 配置注入凭证。
