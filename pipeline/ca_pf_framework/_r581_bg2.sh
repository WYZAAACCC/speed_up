#!/bin/bash
# _r581_bg2.sh --- ★★★★★★★ **C2 修正版单变量**（`BG1` 因"种子撑满盒子"作废）
#
# ## 为什么重跑（R181）
# `BG1` 用 `--plate-L 4000` nm，而 **盒边长 = 64 × 62.5 = 4000 nm** ⇒ **种子横跨全盒**
# ⇒ `a_lath` 只读到 1898 nm、长度被盒钉死 ⇒ **问不出"引擎保不保得住长宽比"**。
#
# ## 本臂（**唯一改动仍是种子三尺寸**，但**缩到盒内**）
# | 臂 | `--plate-L/W/T`（nm） | 起点长宽比 | L / 盒边 |
# |---|---|---|---|
# | `BK6`（参照） | 1000 / 500 / 510 | 2:1:1 | 25% |
# | **★ `BG2`** | **★ 1500 / 150 / 150** | **★ 10:1:1** | **37.5%** |
#
# ## 判据（**与 R181 预先写死的一致**）
# | `a_lath`/`n_lath` 在 step 10–60 | 判决 |
# |---|---|
# | **保持 ≥3** | **✅ 引擎**能**保住各向异性 ⇒ R180 主因是"种子不板条"** |
# | **塌到 ~1** | **❌ 引擎自己抹平 ⇒ 主因是动力学** |
# | **1–3** | **⚠ 两者都有份** |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_blk"
TAG="BG2"
LOG=_w2_r581_bg2.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

BASE="--N 64 --dx-nm 62.5 --steps 60 --every 5 --snap-every 50 \
  --pair-every 10 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 74 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1500 --plate-W 150 --plate-T 150 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6"
m=20
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")

say "=== R581-R181b：C2 修正版（种子 1500/150/150，L 只占盒的 37.5%）==="
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存：available=${avail} MB"
[ "$avail" -lt 3000 ] && { say "❌ 内存不足"; exit 3; }

if [ -d "$ROOT/dry_$TAG" ]; then
  mv "$ROOT/dry_$TAG" "$ROOT/dry_${TAG}_superseded_$(date '+%Y%m%d_%H%M%S')"
  say "旧的已 mv 归档"
fi

say "起 $TAG（cores 16-19）"
setsid nohup env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 16-19 $PY -u _bk_exp.py $BASE \
  --out "$ROOT" --tag "$TAG" --laths "$laths" \
  > "_w2_r581_blk_${TAG}.log" 2>&1 < /dev/null &
disown 2>/dev/null || true
sleep 20
for p in $(pgrep -f "_bk_exp.py.*--tag $TAG" 2>/dev/null); do
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  say "  pid=$p RSS=${rss}MB 在跑 ✓"
done
say "=== 已起（60 步 ⇒ ~5–8 min）==="
