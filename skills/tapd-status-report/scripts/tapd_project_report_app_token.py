#!/usr/bin/env python3
"""
TAPD 项目状态汇报脚本（应用密钥版，脱敏）

功能：
1) 汇总需求/缺陷/任务总数
2) 列出进行中的迭代（默认 status=open）

鉴权：
- 默认使用 TAPD 应用鉴权（client_credentials）换取 access_token
- 支持直接传入现成 token（TAPD_ACCESS_TOKEN）

只读约束：
- 业务数据接口仅允许 GET 且仅允许白名单路径
- 不包含任何创建/修改/删除类业务接口调用
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_BASE_URL = "https://api.tapd.cn"
TOKEN_PATH = "/tokens/request_token"
READ_ONLY_ENDPOINTS = frozenset({
    "/stories/count",
    "/bugs/count",
    "/tasks/count",
    "/iterations",
})


def _require(name: str, value: str | None) -> str:
    if value:
        return value
    raise ValueError(f"缺少必填参数/环境变量: {name}")


def _unwrap_item(item: Any) -> dict[str, Any]:
    if isinstance(item, dict) and len(item) == 1:
        only_value = next(iter(item.values()))
        if isinstance(only_value, dict):
            return only_value
    return item if isinstance(item, dict) else {}


@dataclass
class TapdAppClient:
    base_url: str
    workspace_id: str
    app_id: str | None = None
    app_secret: str | None = None
    access_token: str | None = None
    timeout: int = 20

    _token_expire_at: float | None = None

    def _request_json(self, req: urllib.request.Request, body: bytes | None = None) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(req, data=body, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"网络请求失败: {exc}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"接口返回非 JSON: {raw[:200]}") from exc

        if not isinstance(payload, dict):
            raise RuntimeError(f"接口返回结构异常: {payload}")
        return payload

    def _need_refresh_token(self) -> bool:
        if not self.access_token:
            return True
        if self._token_expire_at is None:
            return False
        return time.time() >= self._token_expire_at - 30

    def _ensure_access_token(self, force_refresh: bool = False) -> str:
        if not force_refresh and not self._need_refresh_token():
            return _require("TAPD_ACCESS_TOKEN", self.access_token)

        if not self.app_id or not self.app_secret:
            raise ValueError("缺少 TAPD_APP_ID/TAPD_APP_SECRET，无法换取 access_token")

        auth_raw = f"{self.app_id}:{self.app_secret}".encode("utf-8")
        basic_auth = base64.b64encode(auth_raw).decode("ascii")
        token_url = f"{self.base_url}{TOKEN_PATH}"
        req = urllib.request.Request(
            url=token_url,
            method="POST",
            headers={
                "Authorization": f"Basic {basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8")
        payload = self._request_json(req, body=body)

        if payload.get("status") != 1:
            raise RuntimeError(f"token 获取失败: info={payload.get('info')}")

        data = payload.get("data") or {}
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"token 获取失败: 未返回 access_token, data={data}")

        self.access_token = str(token)
        expires_in_raw = data.get("expires_in")
        try:
            expires_in = int(expires_in_raw) if expires_in_raw is not None else 0
        except (TypeError, ValueError):
            expires_in = 0

        if expires_in > 0:
            self._token_expire_at = time.time() + expires_in
        else:
            self._token_expire_at = None

        return self.access_token

    def _request_readonly(self, path: str, params: dict[str, Any], retry_auth: bool = True) -> dict[str, Any]:
        if path not in READ_ONLY_ENDPOINTS:
            raise ValueError(f"禁止访问非只读白名单接口: {path}")

        token = self._ensure_access_token()
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{self.base_url}{path}?{query}"
        req = urllib.request.Request(
            url=url,
            method="GET",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        payload = self._request_json(req)
        if payload.get("status") == 1:
            return payload

        info_text = str(payload.get("info") or "").lower()
        should_retry = retry_auth and any(k in info_text for k in ["token", "expire", "invalid"])
        if should_retry:
            self._ensure_access_token(force_refresh=True)
            return self._request_readonly(path, params, retry_auth=False)

        raise RuntimeError(f"TAPD 接口调用失败: {path}, info={payload.get('info')}")

    def get_count(self, resource: str) -> int:
        payload = self._request_readonly(
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

            payload = self._request_readonly("/iterations", params)
            rows = payload.get("data") or []
            if not isinstance(rows, list) or not rows:
                break

            normalized = [_unwrap_item(item) for item in rows]
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
    parser = argparse.ArgumentParser(description="生成 TAPD 项目状态汇报（应用密钥版）")
    parser.add_argument("--base-url", default=os.getenv("TAPD_API_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--workspace-id", default=os.getenv("TAPD_WORKSPACE_ID"))
    parser.add_argument("--app-id", default=os.getenv("TAPD_APP_ID"))
    parser.add_argument("--app-secret", default=os.getenv("TAPD_APP_SECRET"))
    parser.add_argument("--access-token", default=os.getenv("TAPD_ACCESS_TOKEN"))
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
        workspace_id = _require("TAPD_WORKSPACE_ID/--workspace-id", args.workspace_id)
        base_url = _require("TAPD_API_BASE_URL/--base-url", args.base_url).rstrip("/")

        access_token = (args.access_token or "").strip() or None
        app_id = (args.app_id or "").strip() or None
        app_secret = (args.app_secret or "").strip() or None
        if not access_token and (not app_id or not app_secret):
            raise ValueError(
                "需提供 TAPD_ACCESS_TOKEN，或同时提供 TAPD_APP_ID + TAPD_APP_SECRET"
            )

        client = TapdAppClient(
            base_url=base_url,
            workspace_id=workspace_id,
            app_id=app_id,
            app_secret=app_secret,
            access_token=access_token,
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
                "auth_mode": "token_only" if access_token else "app_credentials",
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
