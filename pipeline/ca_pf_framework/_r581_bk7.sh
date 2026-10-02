#!/bin/bash
# _r581_bk7.sh --- ★★★★★★★★ **C6 的真正判决实验**：`--stack-pick-dg 1`
#
# ## 背景（R177 的判决 + 原因）
# * **R177 实测**：`BK6`（默认，`stack_pick_dg=0`）的 `r_selfac` 在**变体标签置换检验**里
#   **p = 0.31–0.33** ⇒ **与随机贴标签无异** ⇒ **C6 在本构型里不成立**；
# * **原因**（`windowB_surface.py:2269` 逐字）：选择是
#   `k = ks[rng.integers(...)]` ⇒ **对已有场均匀随机、完全不看驱动力**；
# * **而引擎里有开关**：`--stack-pick-dg 1`（`_bk_exp.py:2989`，**默认 0**）⇒
#   **把新片接到"外侧面平均 `dG` 最大"的块上**（`:2276` 逐字）。
#   **⚠ `:2275` 说它**从未接过线**（接线缺口 #3）** ⇒ **本实验就是第一次真开它**。
#
# ## 设计（**单变量：只差 `--stack-pick-dg`**）
# | 臂 | 设置 | 状态 |
# |---|---|---|
# | **`BK6`**（已有） | `stack_pick_dg=0`（默认） | 已跑，p=0.31 |
# | **★ `BK7`**（本轮） | **★ `--stack-pick-dg 1`** | 其余**逐字**同 `BK6` |
#
# ## 判据（**预先写死**，同 R177）
# | 观察 | 判决 |
# |---|---|
# | **`r_selfac` 的置换 p **≤0.05**（≤ 5% 分位 **0.619**）** | **✅ 弹性偏置真的改变了变体选择 ⇒ C6 有机制** |
# | **p 仍 ≈0.3（0.05 < p < 0.95）** | **⇒ 连"按 `dG` 选块"也不改变 `r_selfac` ⇒ C6 需另想办法** |
# | **引擎不跑 / 报错 / `Traceback`** | **⚠ 无法判定 ⇒ 先查开关实现是否完整** |
# | **`r_selfac` 反而**变大**（p ≥0.95）** | **★ 反自协调 ⇒ 更大的问题** |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_blk"
TAG="BK7"
LOG=_w2_r581_bk7.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ★ 与 BK6 逐字相同（含 --pair-every 10），**只多一个 --stack-pick-dg 1**
BASE="--N 64 --dx-nm 62.5 --steps 250 --every 5 --snap-every 50 \
  --pair-every 10 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 74 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --stack-pick-dg 1"
m=20
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")

say "=== R581-R178：C6 判决实验（--stack-pick-dg 1）==="
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存：available=${avail} MB（预计 ~2.2 GB）"
[ "$avail" -lt 3000 ] && { say "❌ 内存不足（<3 GB）⇒ 不动"; exit 3; }

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
sleep 25
ok=0
for p in $(pgrep -f "_bk_exp.py.*--tag $TAG" 2>/dev/null); do
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  say "  pid=$p RSS=${rss}MB 在跑 ✓"
  ok=1
done
[ "$ok" = "0" ] && { say "  ❌ 没起来 ⇒ 查日志尾："; tail -5 "_w2_r581_blk_${TAG}.log" | cut -c1-100 | sed 's/^/    /' | tee -a "$LOG"; }
say "=== 已起（250 步 ⇒ ~1.5–2 h）==="
