#!/usr/bin/env bash
# _bk_commit_r9b.sh —— 提交 Round 9 收尾
set -eu
cd /mnt/f/speed_up || exit 1
git add -A pipeline/ca_pf_framework/_bk_measure.py \
           pipeline/ca_pf_framework/_bk_exp.py \
           pipeline/ca_pf_framework/_bk_pair.py \
           pipeline/ca_pf_framework/_bk_verdict.py \
           pipeline/ca_pf_framework/BLOCK_STATUS.md
git commit -q -F - <<'MSG'
Round 9 收尾：修正生效（预登记预测成立）+ V-3g/V-5b/V-7 三条判据口径修正

## 预登记预测成立（dry_gs3, --nuc-overlap-nm 94）
step50:  F3 0.4742→1.5469 µm²，覆盖率 0.288→1.069，β 占比 0.62→0.13
step100: F3 2.4948→4.8561 µm²，覆盖率 0.513→1.287，β 占比 0.61→0.12~0.14
⇒ 每对 β 占比落到**预装臂底噪水平(0.14~0.16)**，投影间隙由 +26~+29 nm（缝）
  变成 −38~−109 nm（重叠），与"中面定界面"的机理一致。
⚠ 副作用：咬入把先形成的板条吃掉一块（gs3@100 板条1 751 体素 vs gs2 1871，−60%）
  ⇒ 94 nm 太大；理论下限是 overlap ≥ 1.0Δx=62.5 nm。已启动 dry_gs4 作剂量-响应第二点。

## 单一实现（避免判据分叉）
V-7/V-7b 的算法收进 _bk_measure.snapshot_coverage()，_bk_pair.py 与 _bk_verdict.py 共用。
回归检验：重构后 gs2/pa 的全部 V-7 数字与重构前逐位一致，自检 0 FAIL。

## V-5 → V-5b：显著碎裂
_bk_measure 新增 _ncomp_sizes()/_ncomp_big()（_ncomp 语义不变，分量个数逐位一致）。
ncompbig_max（≥32 体素）进 CSV 与判决。新增 3 条自检：
  C15  1 根板条 + 3 个 1 体素孤儿 ⇒ ncomp=4 但 ncompbig=1（精确复刻 gs2 实跑）
  C15b 孤立 3 体素 ⇒ ncompbig=0
  C15c 反向对照：真切断 ⇒ ncompbig ≥ 2
⇒ 自检 19 条 0 FAIL。

## V-3 → V-3g：生长臂必须剔除形核步
f3_pos_dx 是所有 F3 面的平均位置，每次形核凭空多一张界面 ⇒ 平均必然跳变。
gs2 实测 Δpos 在 30/40/50 步恒为 +0.000，60 步（第 3 个核）跳到 −2.717
⇒ 原 V-3 读 max=3.417 Δx 判 FAIL，但这不是界面迁移。
V-3g：剔除 nslab_n 变化的测点后 max|ΔΔpos| < 0.12 Δx
⇒ 实测 0.0434 Δx（13 个非形核测点）PASS。

## V-2 对堆叠过强（如实报，不改阈值）
dry_pa（预装）V-2 FAIL：中段板条体积略降 —— 与 §5.1 推导一致（内层宽面 F3、
Δf=Δe_el≡0 ⇒ 无体驱动力，只受 F3 面积最小化支配）。适用范围应限定为有 F1 面积的板条；
整块堆叠的正确判据是总体积增长（gs2 0.3784→2.6208，pa 2.246→2.605 µm³）。

## 又两个量具自伤 bug（不影响已落盘数据）
1. dp=max([nan,...]) ⇒ V-3 假 FAIL，V-6 把 0.236/nan=inf 报成 PASS。加 isfinite 过滤。
2. V-1g 静默不判：只查 meta['grow_stack']，而 gs2 是补 meta 字段之前跑的
   ⇒ 该行干脆不出现，极易读成"过了"。改为数据侧判据（nslab_n 首值 < M）。
   修好后 gs2 的 V-1g 明确 PASS：阶梯 1→2→3→4→5→6，级数 5。
MSG
git log --oneline -1
