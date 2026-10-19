#!/usr/bin/env python3
"""从 PyPI 下载指定包的 sdist 并解包到 src/。

用法: fetch_sdist.py <name> <version>
解包后的顶层目录写入 $GITHUB_OUTPUT 的 srcdir 键。
"""
import io
import json
import os
import pathlib
import sys
import tarfile
import urllib.request

name, version = sys.argv[1], sys.argv[2]

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
print(f"srcdir={out}", flush=True)
gh_out = os.environ.get("GITHUB_OUTPUT")
if gh_out:
    with open(gh_out, "a") as f:
        f.write(f"srcdir={out}\n")
