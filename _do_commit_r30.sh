#!/bin/bash
# R30 提交脚本 —— 只提交 R30 的显式路径（不碰 R1 遗留的未提交改动）
set -eu
cd /mnt/f/speed_up || exit 1

git add \
  pipeline/ca_pf_framework/R30_AUDIT_LEDGER.md \
  pipeline/ca_pf_framework/BLOCK_SELFAC.md \
  pipeline/ca_pf_framework/R30_AUDIT_S1_PARALLEL.md \
  pipeline/ca_pf_framework/R30_AUDIT_S2_MEASURE.md \
  pipeline/ca_pf_framework/R30_AUDIT_S3_LAGB.md \
  pipeline/ca_pf_framework/R30_AUDIT_S4_SELFAC.md \
  pipeline/ca_pf_framework/R30_AUDIT_S5_DUMP.md \
  pipeline/ca_pf_framework/_bk_measure.py \
  pipeline/ca_pf_framework/_bk_exp.py \
  pipeline/ca_pf_framework/_bk_verdict.py

# R30 新增脚本 / 日志 / 结构化产物（只匹配 _r30_ / R30_ 前缀）
# ⚠ `*.log` 在 .gitignore 里 ⇒ 逐文件 `|| true` 跳过（报告里已给复现命令）
for f in pipeline/ca_pf_framework/_r30_*; do git add -- "$f" 2>/dev/null || true; done
for f in pipeline/ca_pf_framework/_w2_r30_*; do git add -- "$f" 2>/dev/null || true; done
for f in pipeline/ca_pf_framework/_exp/r30_*; do git add -- "$f" 2>/dev/null || true; done

git commit -F - <<'MSG'
R30 ★★★ 「块 = 多根同类板条堆叠 + 低角晶界分隔」的框架与代码深度审计 + 三项 P0 修复

## 审计（5 个并行只读子审计 + 主代理逐条复核）
- 新增 R30_AUDIT_LEDGER.md：P0×7 / P1×12 / P2×6 + 「已复核为非问题」5 条 + 影响面表 + 修复顺序
- 子审计报告 S1..S5（并行 / 量具 / LAGB-薄膜 / 自协调 / 落盘），共 2700+ 行，全部可复现

## 三条最严重的发现（都经我独立重跑复核）
- P0-1 块"形成"的主判据 nslab_n/nf3_col 有**两种静默少读**：
  min_run=2 丢掉只占 1 个箱的薄层（实测 6 层 2Δx 读成 5）；r_col=300nm 硬编码
  且不落盘 ⇒ 面内偏置的板条整个不可见（正在跑的 dry_cln11 step2000 就是这一例）
- P0-4 全量状态**没落盘**：297 个快照里 phi 键出现 0 次；--phi-every 的 help 与
  代码相反（写"0=与 snap-every 相同"，实为"0=从不"）⇒ 用户"全部数据留盘可事后
  重测"的硬要求对需要 φ 的量不成立
- P0-7 advance 的多核并行：层写得对（逐位相同，5 判据+2 对照全过），但**最贵的
  算子 upwind_flux_vec 在生产路径上一次都没并行**（调用点在 for_each 的 worker
  里 ⇒ 死锁守卫强制分段数=1；实测 12/12 次 nth=1）；加速比只有 ×1.9-2.3@4

## 已修复（先量具后物理，全部带正/负对照；R8 逐位回归 0 差异）
- P0-1：column_profile 加 min_run；measure_state 加自适应 r_col（**逐胞取最大**，
  不是包围盒半对角线——后者实测只给 0.88 覆盖）+ 可见性守卫 col_cover_*。
  **两个口径都存**：旧列逐位不变（历史可复现），新增 nslab_n1/runs1/nf3_col1/
  r_col_nm/col_cover_min 供判决；_bk_verdict 的 V-1/V-7/V-8 已切换（老归档自动回退）
  ⇒ _r30_mfix_smoke.py 6 条对照全过
- P0-4：实现**带内稀疏 φ**（band_idx/band_val/band_fld/band_cells）+ 落盘 Δpos 基准
  f3_pos_p0_m + psi + t_s；--phi-every 文案改正，新增 --phi-band-every（默认每个
  快照都存，代价实测 6.8% 整场 φ）
  ⇒ _r30_bandchk.py 5 条对照全过，并抓到一条必须记账的限制：带宽 bc 胞 ⇒
    一阶导只在 (bc-1)Δx、二阶导（曲率）只在 (bc-2)Δx 内层可逐位重算
- P0-5：V-8/V-8b 的时间基统一到最后快照的 step 并把实际 step 打印出来
  （cln11 的现场 FAIL 是 CSV 末行 vs 最后快照不一致造成的伪影）

## 新框架（目标第 2 项的框架补全）
- 新增 BLOCK_SELFAC.md：补上"群级（多块）"这一空层。**最小自协调规模 k*=6**，
  且 r<tol 的六元组恰是 **64 个 = 6 个 {110}β 惯习面各取一个**（2^6，穷举实测）；
  k≤5 无解；文献常说的 <111>β 三元组 r=0.323 **并不自协调**；tr(ε⁰) 全变体逐位
  相同 ⇒ 体积项不可能被自协调
- 该判据经**两条不共用代码**的独立路线复核（SLSQP + 单纯形随机采样）：第一版
  投影梯度**没收敛**（17/40 个子集被 SLSQP 找到更低值，最大相对差 1.01e-01），
  换成欧氏单纯形投影后 max 相对差 7.33e-16；k*=6 与 64 的结论独立复算不变

## 回归
- _r30_regress.sh：归档默认路径重跑 200 步，与归档 eng12 的共有列**差异字段数=0**；
  新列非空；_bk_measure.py --selftest FAIL=0 ⇒ 本轮改动没有动任何动力学
MSG

git --no-pager log --oneline -1
echo "--- 已提交文件数 ---"
git --no-pager show --stat --oneline HEAD | tail -5
