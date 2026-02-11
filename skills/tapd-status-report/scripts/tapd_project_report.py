#!/usr/bin/env python3
"""
TAPD 项目状态汇报脚本（脱敏版）

功能：
1) 汇总需求/缺陷/任务总数
2) 列出进行中的迭代（默认 status=open）

鉴权：
- TAPD_API_USER
- TAPD_API_PASSWORD
- TAPD_WORKSPACE_ID
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_BASE_URL = "https://api.tapd.cn"


def _require(name: str, value: str | None) -> str:
    if value:
        return value
    raise ValueError(f"缺少必填参数/环境变量: {name}")


def _unwrap_item(item: Any) -> dict[str, Any]:
    """
    TAPD 列表接口常见返回结构：
    - {"Iteration": {...}}
    - {"Story": {...}}
    - {"Bug": {...}}
    - {"Task": {...}}
    """
    if isinstance(item, dict) and len(item) == 1:
        only_value = next(iter(item.values()))
        if isinstance(only_value, dict):
            return only_value
    return item if isinstance(item, dict) else {}


@dataclass
class TapdClient:
    base_url: str
    api_user: str
    api_password: str
    workspace_id: str
    timeout: int = 20

    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{self.base_url}{path}?{query}"
        auth = base64.b64encode(f"{self.api_user}:{self.api_password}".encode("utf-8")).decode(
            "ascii"
        )
        req = urllib.request.Request(
            url=url,
            method="GET",
            headers={
                "Authorization": f"Basic {auth}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = resp.read().decode("utf-8")
        payload = json.loads(body)
        if payload.get("status") != 1:
            raise RuntimeError(f"TAPD 接口调用失败: {path}, info={payload.get('info')}")
        return payload

    def get_count(self, resource: str) -> int:
        payload = self._request(
            f"/{resource}/count",
            {
                "workspace_id": self.workspace_id,
            },
        )
        data = payload.get("data") or {}
        return int(data.get("count", 0))

    def list_iterations(self, status: str | None, limit: int) -> list[dict[str, Any]]:
        page = 1
        result: list[dict[str, Any]] = []
        while True:
            params: dict[str, Any] = {
                "workspace_id": self.workspace_id,
                "fields": "id,name,status,startdate,enddate",
                "limit": limit,
                "page": page,
            }
            if status:
                params["status"] = status
            payload = self._request("/iterations", params)
            rows = payload.get("data") or []
            if not isinstance(rows, list) or not rows:
                break
            normalized = [_unwrap_item(r) for r in rows]
            result.extend(normalized)
            if len(rows) < limit:
                break
            page += 1
        return result


def render_markdown(
    workspace_id: str,
    story_count: int,
    bug_count: int,
    task_count: int,
    iterations: list[dict[str, Any]],
    iteration_status_filter: str | None,
) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filter_label = iteration_status_filter if iteration_status_filter else "全部状态"

    lines: list[str] = []
    lines.append(f"## TAPD 项目状态汇报（workspace: {workspace_id}）")
    lines.append("")
    lines.append(f"- 生成时间: {now}")
    lines.append("")
    lines.append("### 总量")
    lines.append(f"- 需求（Story）: {story_count}")
    lines.append(f"- 缺陷（Bug）: {bug_count}")
    lines.append(f"- 任务（Task）: {task_count}")
    lines.append("")
    lines.append(f"### 迭代列表（筛选: {filter_label}）")
    if not iterations:
        lines.append("- 无迭代数据")
    else:
        for item in iterations:
            i_id = item.get("id", "-")
            name = item.get("name", "-")
            status = item.get("status", "-")
            start = item.get("startdate", "-")
            end = item.get("enddate", "-")
            lines.append(f"- #{i_id} {name} | status={status} | {start} ~ {end}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 TAPD 项目状态汇报（总量 + 迭代）")
    parser.add_argument("--base-url", default=os.getenv("TAPD_API_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-user", default=os.getenv("TAPD_API_USER"))
    parser.add_argument("--api-password", default=os.getenv("TAPD_API_PASSWORD"))
    parser.add_argument("--workspace-id", default=os.getenv("TAPD_WORKSPACE_ID"))
    parser.add_argument(
        "--iteration-status",
        default="open",
        help="迭代状态筛选。默认 open；传空字符串可查询全部状态。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="每页数量，TAPD 上限通常为 200。",
    )
    parser.add_argument(
        "--format",
        choices=["md", "json"],
        default="md",
        help="输出格式，默认 md。",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        client = TapdClient(
            base_url=_require("TAPD_API_BASE_URL/--base-url", args.base_url).rstrip("/"),
            api_user=_require("TAPD_API_USER/--api-user", args.api_user),
            api_password=_require("TAPD_API_PASSWORD/--api-password", args.api_password),
            workspace_id=_require("TAPD_WORKSPACE_ID/--workspace-id", args.workspace_id),
            timeout=20,
        )

        story_count = client.get_count("stories")
        bug_count = client.get_count("bugs")
        task_count = client.get_count("tasks")

        iteration_status_filter = args.iteration_status.strip()
        if iteration_status_filter == "":
            iteration_status_filter = None
        iterations = client.list_iterations(status=iteration_status_filter, limit=args.limit)

        if args.format == "json":
            output = {
                "workspace_id": client.workspace_id,
                "generated_at": dt.datetime.now().isoformat(),
                "counts": {
                    "stories": story_count,
                    "bugs": bug_count,
                    "tasks": task_count,
                },
                "iteration_filter": iteration_status_filter,
                "iterations": iterations,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(
                render_markdown(
                    workspace_id=client.workspace_id,
                    story_count=story_count,
                    bug_count=bug_count,
                    task_count=task_count,
                    iterations=iterations,
                    iteration_status_filter=iteration_status_filter,
                )
            )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
