---
name: gate0-frozen-reproducibility
description: Gate 0 完成情况 + 生产数据用的是占位溶质参数（NN 数据集可能受污染）+ 一个自己造成的"伪外部 SIGKILL"坑
metadata: 
  node_type: memory
  type: project
  originSessionId: b6decc92-d1df-4297-b052-ad15b31c0547
  modified: 2026-09-18T12:44:05.876Z
---

2026-09-18 完成 Gate 0（冻结可重复性）。完整记录在 **`F:\speed_up\pipeline\GATE0_PROGRESS.md`**（断点续做的唯一依据）。

## 最重要的两条发现

**1. 现有生产数据用的是占位溶质参数，不是 Ti64 真实值。**
`/root/work/s1d_nonad/N.i`（2026-09-18 02:55）里是 `c0=0.35`、`A_part=0.45`（⇒ k=0.5），
而仓库版早已是 `c0=0.036`、`A_part=0.264`（⇒ k=0.63）。反证：`N_out.csv` 首行
`total_solute = 2.2575e-08 = 0.35 × 域面积 6.45e-8`。产物 `N.e`（180 MB，90 步）。

根因：`run_nonad_prod.sh` 从 `/root/work/s1d_w/`（09-17 旧快照）`cp` 源文件，仓库更新从未进入生产。
⇒ **`/root/work/ds_full` / `ds_fine` / `ds_smooth` 这批 NN 数据集是从生产跑派生的，
其溶质部分是占位物理**——用之前必须查清它们具体来自哪次跑。已修：脚本改为从仓库取 + 哈希校验 + 源输入校验。

**2. 同一失效模式还咬过一次**：脚本第 56 行用 `re.sub` 把 `nl_abs_tol` **无条件覆盖**回 `1e-6`
（理由是已被推翻的"7.3e-07 残差地板"）。⇒ 只改源文件是无效的。现已全部改为**断言**（漂了就报错退出）。

## 生产配置（已定）

`nl_abs_tol=1e-9`、初始 `dt=1e-7`、`dtmax=2e-6`（不动）、`l_max_its=300`、
`time_step_interval=1`（用户决定每步都存）、真实 Ti64 参数。

## 代价（实测）

全尺寸：峰值 RSS **3.45 GB**、雅可比装配 25–27 s、每步 **4–5 分钟**、牛顿迭代 6–8 次/步。
`1e-9` 相对 `1e-6` 的代价：**牛顿迭代 2.86×**（3.14→7.00 次/步）。推完整算例约 11–15 小时（外推）。

## 一个"我自己造成的、还误判过"的坑（值得单独记）

全尺寸长跑前后死了四次（退出码 137）。我一度判定为"外部 SIGKILL、原因未定"，
并排除了 OOM（24 GB 只用 3.5 GB）、WSL 重启（uptime 连续）、我自己的 pkill 三个假设。

**真因**：`run_nonad_prod.sh:36-37` 有一段
`pgrep -f 'phase_field-opt -i' | xargs kill -9` —— 它按命令行匹配，**无条件杀掉全机器
的每一个 MOOSE 进程**。而我为了测试这个脚本，反复用 `head -N` 截断后运行它，
截断版**仍然包含这段 preamble**，于是每次测试都把自己的长跑杀了。

⇒ 两条通用教训：
1. **脚本里不限作用域的 `kill -9` 是常驻破坏源**。已改为只清 `cwd == $D` 的进程。
2. **`head -N` 截断脚本不能去掉开头的副作用**。排除法排除三个假设后，
   应该继续查**自己执行过的每一条命令**，而不是跳到"外部原因、原因未定"。

## 仍然保留的改动：checkpoint（通用长跑韧性）

`Checkpoint` 的 `wall_time_interval` 默认 **3600 s**，而 `Output.C:138-141` 的逻辑要求
**显式设 `time_step_interval`** 才按步数存。已改为 `time_step_interval = 10` 并实测
`--recover` 可用（从 step 10 恢复到 11→16）。
**续跑必须用与原始运行相同的 `file_base`**，否则报 `Error opening ExodusII mesh file`。

## Gate 1 进展（2026-09-18 晚）

- **纯晶粒长大 `R²∝t` 已验证**：线性度 0.99994，截距与 R0² 精确吻合，M_eff 与
  M0·exp(−Q/kbT) 在 1–2% 内一致。
- **越界在纯晶粒长大下随加密收敛到零**（d/dx = 2/4/8 → 0.79% / 0.071% / 0）
  ⇒ 越界主体是数值离散热化，**但生产的 2–7% 另有成因**（熔化开关 μ 过零）。
- **LPBF 工况 W/(D/V) = 476**（d=2µm、D_L=2.52e-9、V=0.6m/s），落在扫描范围最顶端。
- **基准必须用"全场均匀温度 + 驱动力"而非"冻结温度梯度"**：后者的 W 被温度梯度
  抹宽 20 倍（μ→0 处界面宽发散），`W/(D/V)` 失去定义。
- 详见 `F:\speed_up\pipeline\GATE1_PLAN.md`。

相关：[[neural-operator-pipeline-state]]、[[solver-choice-mumps-vs-asm]]、[[lpbf-roadmap]]

## ⚠ 生产模型的 kappa_c 缺口（2026-09-18 发现，**重要**）

`c` 的界面宽 `w_c = sqrt(kappa_c/k_c)` 必须 << `η` 的界面宽 `ξ`，否则溶质剖面跟不上 η、
分凝被抹平。**生产配置 `kappa_c = 1.125e-11` 给出 `w_c = 3.54 µm`，
比晶界宽 `d = sqrt(2κ/μ0) = 2 µm` 还大。**

而 `verify_partition.i`（验证 k = 1/(1+2A/k_c) = 0.630）用的是
**`kappa_c = 1e-14`、`M = 1e-6`，不是生产值** ⇒ **生产的分配系数从未在其自身 kappa_c 下验证过。**

实测（静止界面控制）：kappa_c = 1.125e-11 → k_eff 漂到 0.6947（+10.2%）；
kappa_c ≤ 1e-14 → k_eff = 0.6303 精确。
