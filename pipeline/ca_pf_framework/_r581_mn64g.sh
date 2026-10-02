#!/bin/bash
# _r581_mn64g.sh --- ★★★★★ **臂 H：只改 `--plate-L 8000`（S3）—— 同时测 C2 与 C5**
#
# ## 依据（R104 的统一）
# R104 读 `windowB_surface.py:2132-2135` 查明：**`cov` 拒的是"核会压到已转变胞"**
# ⇒ **`cov` = 50–54 不是判据太严，是**空间快被占满****（根数越多 ⇒ `cov` 越多，三条臂自洽）。
# **⇒ 于是 C5 在"形核"模式下是**自限**的 ⇒ 只能靠**每根长得更长**去填满。**
# **⇒ 而 `--plate-L 1000 nm` 把每根钉在 1 µm**（C2 实测 1.0–1.7 µm vs 文献 8.1 µm）。
# **⇒ ⇒ C2 与 C5 是**同一个根因**：`plate_L`（S3 早已判定应改 1000 → 8000）。**
#
# ## 本臂 = 臂 B 的**单变量**延续
# | 臂 | `m` | `--plate-L` | `--nuc-overlap-nm` | 测的是 |
# |---|---|---|---|---|
# | B | 12 | **1000** | 62.5 | 基准（max 11） |
# | **H** | 12 | **8000** | 62.5 | **★ 只改 `plate_L`** |
#
# ## 判据（**预先写死**）
# * **最大分量的最长边显著变长（→ 数 µm）** ⇒ **C2 改善**；
# * **体积分数显著上升** ⇒ **C5 朝目标走**（并给出倍数）；
# * **`cov` 计数下降** ⇒ **确认"空间竞争"机制**（R104）；
# * **两者都没变** ⇒ **`plate_L` 不是 C2/C5 的约束** ⇒ 另查（**不许强行解释**）。
# ⚠ 用 `_r581_blk3d.py`（3-D 连通分量）**同时**出 C2/C5 的数 —— 不依赖柱剖面口径。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64_STEPS:-250}"
LOG=_w2_r581_mn64g.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
_n_mn64() {
  ps -eo args --no-headers 2>/dev/null \
    | grep '_bk_exp\.py' | grep -v grep | grep -c -- '--out _exp/_bk_mn64'
}

say "=== R581-R104：臂 H —— 只改 --plate-L 8000（同时测 C2 与 C5）==="
say "阶段 1：等臂 D/E/F/G 跑完…"
_w=0
while [ "$(_n_mn64)" -gt 0 ]; do
  sleep 30; _w=$((_w + 1))
  [ "$_w" -ge 600 ] && { say "❌ 等了 5 h ⇒ 退出"; exit 4; }
done
say "阶段 1 完成"

avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存闸：MemAvailable = ${avail} MB"
[ "$avail" -lt 1500 ] && { say "❌ 内存不足"; exit 3; }

BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every 100 \
  --pair-every 0 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 5 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis --nfsv-diag 1"

m=12
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")
d="$ROOT/dry_H"
[ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
say "起臂 H：--m 12 --plate-L 8000（**唯一改动**）cores 8-11"
taskset -c 8-11 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag H --laths "$laths" \
    --plate-L 8000 > _w2_r581_mn64_H.log 2>&1
say "臂 H 结束 exit=$? Traceback=$(grep -c '^Traceback' _w2_r581_mn64_H.log || true)"

say "── ★ C2/C5 双判据：臂 B（plate_L=1000）vs 臂 H（8000）──"
for t in B H; do
  if [ -d "$ROOT/dry_$t" ]; then
    say "──── 臂 $t ────"
    $PY _r581_blk3d.py "$t" "$ROOT" 2>&1 | tee -a "$LOG"
  fi
done
say "── 拒绝计数（看 cov 是否下降）──"
$PY _r581_nucdbg.py B H 2>&1 | grep -E "^# 臂|^  (att|ok|cov|nfsv_nofield|n_events|oob|exc) " | tee -a "$LOG"
say "=== R581 MN64G DONE ==="
