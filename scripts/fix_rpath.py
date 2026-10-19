#!/usr/bin/env python3
"""repair 阶段统一给 wheel 内所有 .so 设置 RUNPATH（目标机 Termux 系统库目录）。

背景：C 扩展的链接命令由 cibuildwheel 的 LDFLAGS + setuptools 拼装，
链接期 rpath 参数不可靠地丢失；本机已验证可用的构建产物全部带
RUNPATH=/data/data/com.termux/files/usr/lib。此脚本在 wheel 产出后兜底补齐，
并按 wheel 规范重算 RECORD 的 hash/size（pip 安装时会校验）。

用法: fix_rpath.py <wheel_path> <dest_dir>
"""
import base64
import csv
import hashlib
import os
import subprocess
import sys
import tempfile
import zipfile

RPATH = "/data/data/com.termux/files/usr/lib"


def ensure_patchelf() -> str:
    exe = shutil_which("patchelf")
    if exe:
        return exe
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "patchelf"], check=True
    )
    return shutil_which("patchelf") or sys.exit("patchelf unavailable")


def shutil_which(name: str):
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def patch_so(patchelf: str, path: str) -> None:
    cur = subprocess.run(
        [patchelf, "--print-rpath", path], capture_output=True, text=True
    ).stdout.strip()
    # 去重：RPATH 固定放最前，已存在则先移除，避免重复前缀（Rust 包
    # 链接期常已带 rpath，重复会导致 RUNPATH 值冗余）
    parts = [p for p in cur.split(":") if p]
    if RPATH in parts:
        parts.remove(RPATH)
    parts.insert(0, RPATH)
    new = ":".join(parts)
    subprocess.run([patchelf, "--set-rpath", new, path], check=True)
    # 目标机 bionic 无独立 libpthread.so（pthread 符号在 libc.so），CI 里为满足
    # libuv 的 -lpthread 链接注入了 stub；若留在 NEEDED 里，dlopen 会失败。
    subprocess.run(
        [patchelf, "--remove-needed", "libpthread.so", path],
        capture_output=True,
        text=True,
    )


def sha256_rec(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def update_record(td: str) -> None:
    infos = [d for d in os.listdir(td) if d.endswith(".dist-info")]
    if not infos:
        return
    rec_path = os.path.join(td, infos[0], "RECORD")
    if not os.path.isfile(rec_path):
        return
    with open(rec_path, newline="") as fh:
        rows = list(csv.reader(fh))
    for row in rows:
        if len(row) < 3:
            continue
        rel = row[0]
        if rel.endswith("RECORD"):  # RECORD 自身：hash/size 必须留空
            row[1] = row[2] = ""
            continue
        full = os.path.join(td, rel)
        if os.path.isfile(full):
            data = open(full, "rb").read()
            row[1] = sha256_rec(data)
            row[2] = str(len(data))
    with open(rec_path, "w", newline="") as fh:
        csv.writer(fh).writerows(rows)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    wheel, dest_dir = sys.argv[1], sys.argv[2]
    patchelf = ensure_patchelf()
    os.makedirs(dest_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(wheel) as zf:
            zf.extractall(td)
        n = 0
        for root, _dirs, files in os.walk(td):
            for fname in files:
                if fname.endswith(".so"):
                    patch_so(patchelf, os.path.join(root, fname))
                    n += 1
        update_record(td)
        out = os.path.join(dest_dir, os.path.basename(wheel))
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(td):
                dirs.sort()
                for fname in sorted(files):
                    full = os.path.join(root, fname)
                    zf.write(full, os.path.relpath(full, td))
    print(f"[fix-rpath] {os.path.basename(wheel)}: patched {n} .so -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
