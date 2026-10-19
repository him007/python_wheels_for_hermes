#!/usr/bin/env python3
"""给 cibuildwheel 的 Android Python sysconfig 注入 Termux 链接参数。

背景：C 扩展（setuptools/distutils）的链接命令来自 sysconfig 的 LDSHARED。
pbs (python-build-standalone) 的 Android LDSHARED 既不链接 libpython3.14.so
（导致运行时 PyExc_* 等符号解析失败），也不带目标机 rpath（导致系统库找不到）。
本脚本在 build 前原地追加两段参数，与 Termux 本机已验证可用的产物形态对齐：

  NEEDED  libpython3.14.so  +  RUNPATH /data/data/com.termux/files/usr/lib

用法: patch_sysconfig.py <python_prefix>
幂等：参数已存在则跳过；LDSHARED 行不匹配则原样保留（并告警退出码 0）。
"""
import glob
import os
import re
import sys

ADD = " -lpython3.14 -Wl,-rpath,/data/data/com.termux/files/usr/lib"

# libc++ 转发头路径（CIBW_BEFORE_BUILD 写入 /tmp/.cxxv1_path）。
# Termux 用 -isystem 把 c++/v1 加到 CPPFLAGS（autotools 顺序：CPPFLAGS 在 CFLAGS 前）。
# distutils 顺序相反（CFLAGS 在 CPPFLAGS 前），故此处加到 CFLAGS/CXXFLAGS，
# 确保 -isystem<cxxv1> 在 -I<prefix>/include（bionic 头）之前。
CXXV1 = ""
_cxxv1_path = os.environ.get("CXXV1_PATH", "/tmp/.cxxv1_path")
if os.path.exists(_cxxv1_path):
    with open(_cxxv1_path, encoding="utf-8") as f:
        CXXV1 = f.read().strip()
if CXXV1:
    ISYSTEM = f" -isystem{CXXV1}"
else:
    ISYSTEM = ""
    print("[patch-sysconfig] WARN: /tmp/.cxxv1_path not found, skip -isystem inject")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    prefix = sys.argv[1]
    # pbs 的 _sysconfigdata_*.py 在 lib/python3.X/ 直下（CPython 标准布局），
    # 兜底 sysconfig/ 子目录布局
    files = glob.glob(f"{prefix}/lib/python3.*/_sysconfigdata_*.py") or glob.glob(
        f"{prefix}/lib/python3.*/sysconfig/_sysconfigdata_*.py"
    )
    if not files:
        print(f"[patch-sysconfig] no _sysconfigdata_*.py under {prefix} (skip)")
        return 0
    for path in files:
        src = open(path, encoding="utf-8").read()
        if "-lpython3.14" in src and "termux/files/usr/lib" in src:
            print(f"[patch-sysconfig] already patched: {path}")
            continue
        m = re.search(r"'LDSHARED': '([^']*)'", src)
        if not m:
            print(f"[patch-sysconfig] WARN: no LDSHARED key in {path}")
            continue
        patched = re.sub(
            r"('LDSHARED': ')([^']*)(')",
            lambda g: g.group(1) + g.group(2).rstrip() + ADD + g.group(3),
            src,
            count=1,
        )
        # 注入 -isystem<cxxv1> 到 CFLAGS/CXXFLAGS（Termux 方案，distutils 顺序适配）
        if ISYSTEM:
            for key in ("CFLAGS", "CXXFLAGS"):
                km = re.search(rf"'{key}': '([^']*)'", patched)
                if km and f"-isystem{CXXV1}" not in km.group(1):
                    patched = re.sub(
                        rf"('{key}': ')([^']*)(')",
                        lambda g: g.group(1) + ISYSTEM + " " + g.group(2) + g.group(3),
                        patched,
                        count=1,
                    )
                    print(f"[patch-sysconfig]   {key}: prepend {ISYSTEM.strip()}")
        open(path, "w", encoding="utf-8").write(patched)
        new_m = re.search(r"'LDSHARED': '([^']*)'", patched)
        new = new_m.group(1) if new_m else "(unreachable)"
        print(f"[patch-sysconfig] {path}")
        print(f"[patch-sysconfig]   OLD: {m.group(1)}")
        print(f"[patch-sysconfig]   NEW: {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
