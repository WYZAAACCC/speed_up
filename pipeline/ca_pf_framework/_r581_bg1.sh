#!/bin/bash
# _r581_bg1.sh --- ★★★★★★★ **C2 的单变量实验**：引擎能不能**保住**种子的长宽比？
#
# ## 背景（R180 的发现）
# `BK6`（种子 `--plate-L 1000 --plate-W 500 --plate-T 510` nm ⇒ **长宽比 2:1:1**）实测：
#   step 0：`n_lath`=507 nm（厚）、`a_lath`=1043（长）、`w_lath`=442（宽）⇒ **长/厚 = 2.06**
#   step 5+：**三者全部 ~1.25 µm ⇒ 长/厚 → 1.0**（**等轴化**）
# **⇒ 两条候选归因**（**R180 未分**）：
#   **① 种子本身就不"板条"**（2:1:1）；**② 引擎让宽度长得最快（+180%）⇒ 抹平各向异性**。
#
# ## 实验（**单变量：只改种子的三个尺寸**）
# | 臂 | `--plate-L/W/T`（nm） | 起点长宽比 | 状态 |
# |---|---|---|---|
# | **`BK6`**（已有） | **1000 / 500 / 510** | **2 : 1 : 1** | 已跑（→ 等轴） |
# | **★ `BG1`**（本轮） | **★ 4000 / 250 / 200** | **★ 20 : 1.25 : 1** | **其余逐字同 `BK6`** |
#
# ## 判据（**预先写死**）
# | `BG1` 的长/厚（`a_lath`/`n_lath`）在 step 10–60 的表现 | 判决 |
# |---|---|
# | **★ 保持 ≫1（如 ≥3）** | **✅ 引擎**能**保住各向异性 ⇒ ① 是主因（**种子不板条**）** |
# | **★ 仍塌到 ~1** | **❌ 引擎自己抹平 ⇒ ② 是主因（**动力学**）** |
# | **中间（1–3）** | **⚠ 两者都有份 ⇒ 报区间** |
# | **引擎不跑/报错** | **⚠ 无法判定** |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_blk"
TAG="BG1"
LOG=_w2_r581_bg1.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ★ 与 BK6 逐字相同，**只改三个种子尺寸**
BASE="--N 64 --dx-nm 62.5 --steps 60 --every 5 --snap-every 50 \
  --pair-every 10 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 74 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 4000 --plate-W 250 --plate-T 200 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6"
m=20
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")

say "=== R581-R181：C2 单变量（种子 4000/250/200，长宽比 20:1.25:1）==="
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存：available=${avail} MB"
[ "$avail" -lt 3000 ] && { say "❌ 内存不足"; exit 3; }

if [ -d "$ROOT/dry_$TAG" ]; then
  mv "$ROOT/dry_$TAG" "$ROOT/dry_${TAG}_superseded_$(date '+%Y%m%d_%H%M%S')"
  say "旧的已 mv 归档"
fi

say "起 $TAG（cores 16-19；setsid nohup ⇒ 见 P42）"
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
