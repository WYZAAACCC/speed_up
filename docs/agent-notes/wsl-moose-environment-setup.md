---
name: wsl-moose-environment-setup
description: 本机 MOOSE 运行环境：WSL 布局、conda 双环境、**JIT 静默失败**、9p 缓存、卡死抢救；完整手册在仓库 docs/agent-notes/ENVIRONMENT.md
metadata: 
  node_type: memory
  type: project
  originSessionId: 5a8d92ac-94c6-4a23-856f-0d7a42daf5b8
  modified: 2026-09-19T21:09:09.254Z
---

**⚠ 完整手册已单独成文：`docs/agent-notes/ENVIRONMENT.md`（2026-09-20 实测）。**
本笔记只留要点 + 这一轮新测出来的那条。

## 🔴 新测出来的最重要一条：不激活 conda，JIT **静默失败**

2026-09-20 用 `gb_jac-opt` 跑一个带 `ParsedMaterial` 的 1D 小算例，两档对照：

| | 退出码 | 日志 | `.jitcache` |
|---|---|---|---|
| **不激活 conda** | **0** ✅ | `JIT compile failed.` / `Failed to JIT compile expression, falling back to byte code interpretation.` | **不生成** |
| `conda activate moose` | 0 ✅ | 无 | 生成 |

**⇒ 退出码 0、数值也对，只是所有 parsed 表达式退回字节码解释执行 —— 慢几十倍。**
生产输入里有 2181 字符的 `L` 表达式，退化代价是数量级的。

⚠ **反直觉的地方**：**不激活 conda，二进制本身照样能启动** ——
`gb_jac-opt` 的 RPATH 直指 `/root/miniconda3/envs/moose/lib`，`ldd` 显示
`libmesh_opt.so.0` / `libpetsc.so.3.25` 都能解析。**症状不在启动时，只在 JIT 那一步。**

**⇒ 跑完必须查**：`grep -c "JIT compile failed" run.log`（**必须是 0**）。

## 其它要点（详见手册）

* **两个 conda 环境**：`moose`（跑 MOOSE、建 app，有 `mpicxx`）／`ml`（生成器 + torch）。
  `run_nonad_prod.sh` 会来回切两次。
* **算例跑在 ext4（`/root/work`）**，不要在 `/mnt/f` 上跑。
* **生产二进制** `/root/projects/gb_jac/gb_jac-opt`（**不是** `phase_field-opt`，会报
  `'ACGrGrPolyJ' is not a registered object`）。
* **`--check-input` 实测 ≈120 s**，不是秒级，且它在 `executeExecutioner()` **之后**。
* **WSL 卡死**判据是 `ps -e --no-headers | wc -l` 返回 0；`wsl --shutdown` 有时不够，
  要 `wsl.exe --terminate Ubuntu` 再 `--shutdown`。
* **Git Bash → wsl.exe 会吞掉多行/续行/变量** ⇒ 一律写 `.sh` 文件再 `sed 's/\r$//'` 后执行。
* **`/mnt/f` 是 9p（`cache=0x5`）**，对正在追加的文件静默返回过期数据 ⇒ 读 CSV 走
  `validated/robust_csv.py`。
* **杀进程用 `pgrep -x`**，别用 `pkill -f`（会杀掉含该字符串的自己的 shell，退出码 9）。
* 编译用 `-j 8`（unity build 单编译单元 2–4 GB，`-j 12` 会 OOM 搞崩 WSL）。

相关：[[grain-solute-acceleration-project]]、[[moose-api-gotchas]]
