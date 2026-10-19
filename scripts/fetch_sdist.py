#!/usr/bin/env python3
"""从 PyPI 或 git 源下载指定包的源码并解包到 src/。

用法: fetch_sdist.py <name> <version> [source]
  source 省略  -> PyPI: https://pypi.org/pypi/<name>/<version>/json 取 sdist
  source=git+https://github.com/<repo>@<ref>
             -> GitHub archive tarball（如 psutil 的 android git pin）

解包后统一剥离 pyproject 的 [tool.cibuildwheel*] 段：CI 用 CIBW_* 环境变量
全量控制构建，sdist 自带配置（enable = cpython-freethreading 等）会被当前
cibuildwheel 版本 parse 失败而整 job 挂掉。
"""
import io
import json
import os
import pathlib
import re
import sys
import tarfile
import urllib.request

name, version = sys.argv[1], sys.argv[2]
source = sys.argv[3] if len(sys.argv) > 3 else ""

if source.startswith("git+"):
    m = re.match(r"git\+(https://[^@]+)@(.+)$", source)
    if not m:
        sys.exit(f"bad git source: {source}")
    repo, ref = m.group(1).rstrip("/"), m.group(2)
    url = f"{repo}/archive/{ref}.tar.gz"
    print(f"downloading {url}", flush=True)
    raw = urllib.request.urlopen(url, timeout=600).read()
else:
    api = f"https://pypi.org/pypi/{name}/{version}/json"
    data = json.load(urllib.request.urlopen(api, timeout=30))
    sdist = next(u for u in data["urls"] if u["packagetype"] == "sdist")
    print(f"downloading {sdist['filename']} from {sdist['url']}", flush=True)
    raw = urllib.request.urlopen(sdist["url"], timeout=600).read()

src = pathlib.Path("src")
src.mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
    tf.extractall(src, filter="data")

tops = [p for p in src.iterdir()]
if len(tops) != 1:
    sys.exit(f"expected 1 top-level entry in sdist, got: {tops}")

out = tops[0].resolve()


def strip_cibw_config(root: pathlib.Path) -> None:
    """删掉 pyproject 里 [tool.cibuildwheel] 及其子表（本 CI 用 env 全量接管）。"""
    p = root / "pyproject.toml"
    if not p.is_file():
        return
    kept, dropping = [], False
    for line in p.read_text(encoding="utf-8").splitlines(keepends=True):
        s = line.strip()
        if s.startswith("["):
            # lstrip("[") 同时匹配 [tool.cibuildwheel] 与 [[tool.cibuildwheel.overrides]]
            dropping = s.lstrip("[").startswith("tool.cibuildwheel")
        if not dropping:
            kept.append(line)
    new = "".join(kept)
    if new != p.read_text(encoding="utf-8"):
        p.write_text(new, encoding="utf-8")
        print(f"stripped [tool.cibuildwheel] from {p.name}", flush=True)


strip_cibw_config(out)
print(f"srcdir={out}", flush=True)
gh_out = os.environ.get("GITHUB_OUTPUT")
if gh_out:
    with open(gh_out, "a") as f:
        f.write(f"srcdir={out}\n")
