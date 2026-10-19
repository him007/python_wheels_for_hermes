#!/usr/bin/env python3
"""按 GitHub Release 资产重建本 fork 的 simple index 与 pypi JSON。

只分发本仓库自己构建并验证过的 wheel（链接指向 GITHUB_REPOSITORY 的 Release），
不搬运上游条目 —— 上游历史版本不归本 index 维护。

产物（目录名一律 PEP503 normalized，pip 按该形式请求）：
  wheels/simple/<normalized>/index.html   PEP503 HTML（pip 首选 JSON 失败后的回退格式）
  wheels/pypi/<normalized>/json           仿 PyPI legacy JSON API（展示/兼容用）

用法（CI publish job 内或本机）：
  python3 scripts/generate_index.py               # 扫描本仓库全部 wheels-* release
  REPO=owner/name python3 scripts/generate_index.py
"""
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY") or "him007/python_wheels_for_hermes"
BASE = f"https://github.com/{REPO}/releases/download"
SIMPLE = ROOT / "wheels" / "simple"
PYPI = ROOT / "wheels" / "pypi"


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def gh_json(args: str):
    out = subprocess.run(
        ["gh", "api"] + args.split(), capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def collect_assets():
    """-> {normalized_name: [(filename, version, url), ...]}（新版在前）"""
    releases = gh_json(f"repos/{REPO}/releases?per_page=100")
    pkgs: dict[str, list] = {}
    for rel in releases:
        if not rel.get("tag_name", "").startswith("wheels-"):
            continue
        for asset in rel.get("assets", []):
            fn = asset["name"]
            if not fn.endswith(".whl"):
                continue
            parts = fn.split("-")
            if len(parts) < 3:
                continue
            raw_name, version = parts[0], parts[1]
            pkgs.setdefault(normalize(raw_name), []).append(
                (fn, version, asset["browser_download_url"])
            )
    for entries in pkgs.values():
        entries.sort(key=lambda e: e[1], reverse=True)
    return pkgs


SIMPLE_TMPL = """<!doctype html>
<html>
    <head>
        <title>{name}</title>
    </head>
    <body>
        <h1>{name}</h1>
        <ul>
{items}
        </ul>
    </body>
</html>
"""


def write_simple(name: str, entries) -> None:
    d = SIMPLE / name
    d.mkdir(parents=True, exist_ok=True)
    items = "\n".join(
        f'            <li><a href="{url}">{html.escape(fn)}</a> ({ver})</li>'
        for fn, ver, url in entries
    )
    (d / "index.html").write_text(SIMPLE_TMPL.format(name=name, items=items))


def write_pypi(name: str, entries) -> None:
    d = PYPI / name
    d.mkdir(parents=True, exist_ok=True)
    releases: dict[str, list] = {}
    for fn, ver, url in entries:
        releases.setdefault(ver, []).append(
            {
                "filename": fn,
                "url": url,
                "requires_python": None,
                "packagetype": "bdist_wheel",
                "yanked": False,
                "yanked_reason": None,
            }
        )
    doc = {
        "info": {
            "name": name,
            "version": entries[0][1] if entries else None,
            "requires_dist": None,
            "requires_python": None,
            "platform": "UNKNOWN",
            "summary": None,
            "yanked": False,
            "yanked_reason": None,
        },
        "releases": releases,
    }
    (d / "json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))


def write_root_index(names) -> None:
    """PEP503 根页面：/simple/ 目录本身也要能访问（否则浏览器/pip 探测 404）。"""
    items = "\n".join(
        f'            <li><a href="{n}/">{n}</a></li>' for n in sorted(names)
    )
    SIMPLE.mkdir(parents=True, exist_ok=True)
    (SIMPLE / "index.html").write_text(SIMPLE_TMPL.format(name="simple", items=items))


def main() -> int:
    pkgs = collect_assets()
    if not pkgs:
        print("no wheels-* release assets found", file=sys.stderr)
        return 1
    for name, entries in sorted(pkgs.items()):
        write_simple(name, entries)
        write_pypi(name, entries)
        newest = entries[0]
        print(f"[index] {name}: {len(entries)} asset(s), latest {newest[1]}")
    write_root_index(pkgs)
    print(f"[index] done: {len(pkgs)} package(s) -> {REPO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
