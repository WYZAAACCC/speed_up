#!/bin/bash
# _t5_ab_elong.sh --- ★★★★★ 2×2 因子 A/B：`--eng-elong` × `--facet-proj`（测长宽比）
#
# ## 设计（**预先写死**）
# | 臂 | tag      | --eng-elong | --facet-proj | 预期 |
# |----|----------|-------------|--------------|------|
# | A  | t5AB_A   | 0（回退 2.0）| 0（默认）    | **对照**（= 现状）|
# | B  | t5AB_B   | **3.75**    | 0            | 核更扁 ⇒ 长宽比↑ |
# | C  | t5AB_C   | 0           | **1**        | 抑厚 ⇒ 长厚比↑ |
# | D  | t5AB_D   | **3.75**    | **1**        | 两者叠加 |
#
# ## 为什么用 N=80（5 µm）而不是 N=160（10 µm）
# **长宽比是**局部形状**性质，不需要 10 µm 盒**；而 N³ 代价 ∝ N³：
# `(80/160)³ = 0.125` ⇒ **每臂内存 ~1.25 GB、每步 ~2.7 s**
# ⇒ **4 臂可**并行**（≈5 GB，与在跑的 t5V2 共 ~14 GB < 22 GB）**，
#    且 **1400 步约 1 小时**（N=160 同样步数要 ~8 小时）。
# **⚠ 约束**：`plate_L=1000 nm` 在 5 µm 盒里占 1/5 ⇒ **有余量**（引擎的 `elong*R > margin` 检查应过）。
#
# ## 判据（**预先写死**，全部用**已验证**的量具 `_t5_ar2.py`：长/宽 = PCA，厚 = `n_hab`）
# 1. **主判据**：终态 **长宽比 p1/p2** 的中位 —— **B 应 > A**（若 ≈ ⇒ `eng-elong` 无效）；
# 2. **主判据**：终态 **长厚比 p1/p3** 的中位 —— **C 应 > A**（若 ≈ ⇒ `facet-proj` 无效）；
# 3. **D 应 ≥ max(B, C)**（若 < ⇒ 两机制**冲突**，须查）；
# 4. **⚠ 先验**：A 的终态长宽比应 ≈ **2.0–3.0**（= 已跑完的 t5H3 的实测值）⇒ **否则说明 N=80 改变了结论**；
# 5. **⚠ 若 C/D 崩溃或数值异常 ⇒ `--facet-proj` 未经验证**（代码说它"一次都没跑过"）⇒ 记账。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_ab_elong.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════════ 2×2 因子 A/B：eng-elong × facet-proj ════════'
say "设计：A(0,0) 对照 | B(3.75,0) | C(0,1) | D(3.75,1)；N=80（5 µm）；1400 步；并行"
free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

PIDS=""
run() {     # $1=tag  $2=eng-elong  $3=facet-proj
  local TAG=$1 EL=$2 FP=$3
  local ARGS=""
  [ "$EL" != "0" ] && ARGS="$ARGS --eng-elong $EL"
  [ "$FP" != "0" ] && ARGS="$ARGS --facet-proj $FP"
  $PY _t5_short.py --tag "$TAG" --N 80 --nvar 3 --m 24 --B 3 --steps 1400 \
      --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
      --ckpt-every 100 --ckpt-keep 1 --overlap-nm 62.5 $ARGS \
      > _w2_t5_ab_${TAG}.log 2>&1 &
  say "  起 $TAG：eng-elong=$EL facet-proj=$FP  pid=$!"
}

run t5AB_A 0    0
run t5AB_B 3.75 0
run t5AB_C 0    1
run t5AB_D 3.75 1

say '  ── 等待四臂结束（本脚本**一直等**）──'
wait
say '════ 四臂全部结束 ⇒ 自动跑判据 ════'

for t in t5AB_A t5AB_B t5AB_C t5AB_D; do
  echo "" >> "$LOG"
  echo "──────── $t ────────" >> "$LOG"
  tail -3 _w2_t5_ab_${t}.log 2>/dev/null >> "$LOG"
  # 用**已验证**的量具测长宽比（L/W = PCA，厚 = n_hab）
  SNAP=$(ls -1 _exp/_bk_t5/dry_${t}/snap_*.npz 2>/dev/null | sort | tail -1)
  if [ -n "$SNAP" ]; then
    echo "  终态快照 = $SNAP" >> "$LOG"
    $PY _t5_ar2.py "$t" 2>/dev/null | grep -E "长厚比：中位|场 " | tail -8 >> "$LOG" || true
  fi
done
say '════ 判据（**预先写死**）════'
say '  1) B 的长宽比应 > A（否则 eng-elong 无效）'
say '  2) C 的长厚比应 > A（否则 facet-proj 无效）'
say '  3) D 应 >= max(B,C)'
say '  4) ⚠ 先验：A 的终态长宽比应 ≈ 2.0–3.0（= t5H3 实测）'
say '  5) ⚠ 若 C/D 崩溃或异常 ⇒ facet-proj 未经验证'
say '=== AB_ELONG DONE ==='
