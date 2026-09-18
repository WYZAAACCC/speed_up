---
name: wsl-moose-environment-setup
description: 本机 MOOSE 运行环境的搭建方式与踩过的坑（WSL 在 F 盘、代理、根证书、编译参数）
metadata: 
  node_type: memory
  type: project
  originSessionId: 5a8d92ac-94c6-4a23-856f-0d7a42daf5b8
  modified: 2026-09-16T10:08:56.353Z
---

本机（Windows 11，i7-14700HX 12 核/20 线程，32 GB 内存）上 MOOSE 的运行环境。**2026-09-16 搭建完成并跑通。**

## 最终布局

| 项目 | 位置 |
|---|---|
| WSL 发行版磁盘 | `F:\WSL\Ubuntu\ext4.vhdx`（**已从 C 盘迁出**） |
| WSL swap | `F:\WSL\swap.vhdx`（8 GB） |
| MOOSE 源码 | WSL 内 `/root/moose`，版本 `b892bff54e`（2026-08-22） |
| conda 环境 | `/root/miniconda3/envs/moose`，`moose-dev=2026.08.23=mpich` |
| 可执行文件 | `/root/moose/modules/phase_field/phase_field-opt` |
| 实验目录 | `F:\speed_up\phase0a\`（结果同步回这里） |

`.wslconfig`（在 `C:\Users\mycomputer\.wslconfig`）：memory=24GB、processors=20、swapFile 指向 F 盘、**networkingMode=mirrored**。
（注意：`autoMemoryReclaim` 在 WSL 2.7.14 不被识别，别写进去。）

## 关键坑与解法

1. **C 盘只剩 7 GB 时跑了几 GB 下载** → C 盘写满 → WSL ext4 转 `emergency_ro` 只读 → conda 崩、编译残骸一堆。
   **解法**：`wsl --manage Ubuntu --move F:\WSL\Ubuntu`。**永远不要在 C 盘空间紧张时往 WSL 里下载。**

2. **WSL 里 GitHub 解析到 127.0.0.1**（本机 DNS 问题）→ 必须走代理。
   本机跑的是 **Watt Toolkit（Steam++）**，端口 7897。它会对 github.com 做 **TLS 中间人**，用自己的自签根证书。
   **解法**：导出 `Cert:\LocalMachine\Root` 里 CN=SteamTools Certificate 且在有效期内的那张 → 装进 WSL 的 `/usr/local/share/ca-certificates/` → `update-ca-certificates`。**不要去关 git 的 sslVerify。**
   配合 `networkingMode=mirrored`，WSL 里直接用 `127.0.0.1:7897` 即可。

3. **WSL 崩溃会留下 0 字节的 libtool 产物**（`.lo` / `.la`），导致后续报 `not a valid libtool object/archive`。**解法**：`find . -name '*.la' -delete; find . -name '*.lo' -delete; find . -name '*.o' -size 0 -delete` 后重编。

4. **编译并行度不能太高**。MOOSE 用 unity build，单个编译单元 2–4 GB，`-j 12` 会 OOM 把 WSL 整个搞崩。**用 `-j 8`。**

5. **源码版本要和 conda 包匹配**。conda 是 `2026.08.23`，源码应切到 `b892bff54e`（2026-08-22）。会有"required version 2026.08.19"的警告，不影响编译。

6. **命令传递**：Git Bash → PowerShell → WSL 多层引号极易把 `$变量`、`$()`、换行吞掉。**凡是多行或带变量的命令，一律写成 `.sh` 文件再用 `bash 文件` 执行**，并先 `sed 's/\r$//'` 转换行尾。

## 本机代理信息

Watt Toolkit 代理：`127.0.0.1:7897`（mirrored 网络模式下 WSL 可直接用）。

相关：[[grain-solute-acceleration-project]]
