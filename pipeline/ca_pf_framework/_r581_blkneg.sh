#!/bin/bash
# _r581_blkneg.sh --- ★★★★★★★ **C6 的负对照 ①**：`r_selfac` 这个量**有没有分辨力**？
#
# ## 为什么必须先做这个（P6/P21：量具先于结论）
# R174 实测 `BK6`（F 配置 + `--pair-every 10`）在 step 10：
#   `n_habit`=3、`n_var_sig`=3、`f_var`=0.745、**`r_selfac`=0.6683**
# ⇒ 我据 docstring 读它作"自协调残差"。
# **⚠ 但 R175 我指出：0.745 的体积偏斜下残差**本该接近单变体的 1.0**** ⇒
# **⇒ 所以必须**先验这个量**：**单变体时它是不是 ≈1**？**
#
# ## 实验（**单变量：只改 `--laths` 的变体分配**）
# | 臂 | `--laths` | `nv` | 预期 |
# |---|---|---|---|
# | **`BK6`**（已有） | **12 变体 × 20** | **240** | — |
# | **★ `BN1`**（本轮） | **★ 全 1（`[1]×240`）** | **★ 240（不变！）** | **`n_var_sig`=1、`f_var`=1.0 ⇒ `r_selfac` 应 ≈1** |
#
# **★ `nv` **保持 240** ⇒ **只改了"变体分配"这一个变量**** ✓
#
# ## 判据（**预先写死**）
# | 观察 | 判决 |
# |---|---|
# | **`r_selfac` ≈ **1.0**（≥0.99）** | **✅ 量具有分辨力**（**单变体无协调 ⇒ 残差满**）⇒ R174 的 0.6683 是**真的下降** |
# | **`r_selfac` 明显 <1（如 0.6–0.8）** | **❌ 量具**没有分辨力**** ⇒ **R174 的"自协调在发生"作废** ⇒ 必须换量具 |
# | **`n_var_sig` ≠ 1** | **⚠ 实验没按预期构型跑** ⇒ 先查 `--laths` 是否真被接受 |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_blk"
TAG="BN1"
LOG=_w2_r581_blkneg.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

BASE="--N 64 --dx-nm 62.5 --steps 30 --every 5 --snap-every 50 \
  --pair-every 10 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 74 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6"
# ★ **全 1 ⇒ 240 个场全是变体 1**（nv 保持 240）
laths=$("$PY" -c "print(','.join(['1']*240))")

say "=== R581-R176：C6 负对照 ①（单变体，nv 保持 240）==="
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存：available=${avail} MB"
[ "$avail" -lt 3000 ] && { say "❌ 内存不足"; exit 3; }
say "laths 的前 30 个字符：$(printf '%s' "$laths" | cut -c1-30)…"

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
say "=== 已起（30 步 ⇒ ~3–5 min）==="
