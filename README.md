# OpenClaw TAPD Status Plugin

这是一个用于 OpenClaw 的插件仓库，提供 TAPD 需求/缺陷/任务状态汇报技能：

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
        └── SKILL.md
```

## 安全说明

- 仓库不包含真实 TAPD 密钥、密码、Token。
- 运行时请通过环境变量或 OpenClaw 配置注入凭证。
