# python_wheels_for_hermes

Termux (Android · aarch64) 预编译 Python wheel —— 装包不用再等编译。

本仓库是 [nsyhykui/python_wheels_for_termux](https://github.com/nsyhykui/python_wheels_for_termux) 的 **fork**：只保留其中 9 个常用包，用 GitHub Actions 自动构建、发布并维护 pip 索引。上游提供 800+ 包的完整列表与安装教程，找更多包请移步上游。

## 📦 包含的包（9 个）

wheel 标签：`cp314-android_24_arm64_v8a`（CPython 3.14 · Termux · Android API 24+ · arm64-v8a）

| 包 | 版本 | 构建方式 |
|---|---|---|
| cryptography | 50.0.1 | Rust（setuptools-rust，aws-lc-rs） |
| pydantic-core | 2.46.4 | Rust（maturin） |
| watchfiles | 1.2.0 | Rust（maturin） |
| resvg-py | 0.4.0 | Rust（maturin） |
| pillow | 12.3.0 | C（imagequant / raqm 关闭） |
| pillow-heif | 1.7.0 | C（交叉编译 libheif） |
| httptools | 0.8.0 | C |
| ruamel.yaml.clib | 0.2.15 | C |
| firecrawl-anydoc | 0.2.4 | 含原生 .so |

版本以 [`packages.json`](./packages.json) 为准。每次 CI 构建后会自动重建 [simple 索引](https://him007.github.io/python_wheels_for_hermes/simple/) 并回推，pip 源与 Release 始终同步。

## 🚀 快速开始

```bash
pip install --index-url https://him007.github.io/python_wheels_for_hermes/simple/ cryptography
```

⚠️ 注意事项

- **只有上表 9 个包**，不是完整 PyPI。没找到的包请用官方 PyPI，或上游的完整源：`https://nsyhykui.github.io/python_wheels_for_termux/simple/`
- **Python 版本**：仅 cp314（Python 3.14）。上游的 3.13 / 3.12 轮子不在本 fork 维护范围内
- **多源混用**：若你的 pip 配了 `extra-index-url` 且其中含上游源，同版本时 pip 可能优先取上游构建的产物。要确保装的是本 fork 的版本，加 `--isolated`，或临时清空 `PIP_EXTRA_INDEX_URL`
- **动态库依赖**：少数包运行时需要 Termux 系统库。遇到 `dlopen failed: library "libxxx.so" not found` 时，按缺的库名安装对应 Termux 包（去掉 `.so` 后缀）：

  ```bash
  pkg install libjpeg-turbo libwebp libtiff   # 例：pillow 的图像后端
  ```

## 🔧 构建方式

CI（[`.github/workflows/build.yml`](./.github/workflows/build.yml)）在 `packages.json` 或 `scripts/` 变更时触发，共 11 个 job：

1. 从 Termux apt 索引**按包名动态解析** sysroot（python / openssl / 各图像库的 `.deb`）—— 硬编码版本会被仓库顶掉导致 404，故改为解析 + 硬编码回退
2. 从 PyPI 取 sdist，用 cibuildwheel 交叉编译 Android wheel
3. `scripts/fix_rpath.py` 给所有 `.so` 补 `RUNPATH`（去重置顶）并按 wheel 规范重算 RECORD
4. 发布到 GitHub Release，随后重建 `wheels/simple` 与 `wheels/pypi` 索引并回推 main

## 许可证与致谢

- 预编译 `.whl` 基于 [Termux](https://termux.dev/) 官方二进制重新打包，**未对原始上游代码做任何修改**；每个 wheel 内部均包含对应软件的原始许可证（`LICENSE`），使用前请仔细阅读
- 本项目沿用上游的 [Apache-2.0](./LICENSE) 许可证，版权与来源按 [`NOTICE`](./NOTICE) 要求保留：

  > python_wheels_for_termux — Copyright (c) 2026 nsyhykui
  > 原始来源：https://github.com/nsyhykui/python_wheels_for_termux

- 致谢 [Termux](https://termux.dev/) 项目及其贡献者，以及上游作者 [nsyhykui](https://github.com/nsyhykui/python_wheels_for_termux) 的打包与文档工作

## 📅 更新日志

### 2026-10-19
- sysroot 改为按包名从 Termux apt 索引动态解析（修复 python deb 过期 404 导致的全量构建失败）
- publish 后自动重建 simple / pypi 索引并回推；新增 `/simple/` PEP503 根页
- `fix_rpath.py` 对 RUNPATH 去重；启用 GitHub Pages，pip 源与页面链接改指本 fork

### 2026-05-07
- **许可证变更**：从 MIT 切换到 Apache 2.0，新增 `NOTICE` 文件，明确要求保留版权和来源链接

---

⭐ 觉得有用，欢迎 [给本仓库点个 Star](https://github.com/him007/python_wheels_for_hermes)；也欢迎给上游 [nsyhykui/python_wheels_for_termux](https://github.com/nsyhykui/python_wheels_for_termux) 点 Star，支持原作者 🙏
