#!/bin/bash
# _r581_blkarm.sh --- ★★★★★★★ **C6 的直接判据量**：跑一条**多变体 + `--pair-every > 0`** 的臂
#
# ## 为什么这样就能拿到 C6 的量（R172 的更正）
# R164 我以为 `blocks()` 是死代码 ⇒ 错**。真相**（`_bk_exp.py`）：
#   * **`:283`** `b = _BM.blocks(reg, dx, vmap, eps0_var=EPS0, npf_var=NPF, axes_var=ax)`
#   * **`:2345`** `**(_blk_cols(g, reg, dx, vmap) if _pair_now else _BLK_EMPTY),`
#   ⇒ **块表只在 `--pair-every` **命中**时算**（`:102`/`:153` 逐字）
#   ⇒ **所以 `blk_*` / `r_selfac` / `n_habit` / `f_var` 空 = **我没开那个开关**，不是 bug** ✓
#
# ## 这条臂的设计（**照抄 F，只加 `--pair-every`**）
# **F 的配置**（R153，`--nuc-block-target 74`）+ **`--pair-every 10`** + **250 步**
# ⇒ **F 在 250 步时 `V`=7** ⇒ **块表量会在多变体态上落盘** ⇒ **这就是 C6 的直接证据** ✓
#
# ## 判据（**预先写死**）
# | 观察 | 判决 |
# |---|---|
# | **`r_selfac` 列**有值**（非 NaN/空）** | **✅ C6 有直接判据量了** |
# | **`n_habit` / `blk_laths` / `blk_nprof` / `blk_span_nm` 有值** | **✅ goal §(17) 第 2、3 件事可报** |
# | **全空** | ❌ **还有别的东西挡着** ⇒ 查 `_blk_cols` 的 `except` |
# | **`n_habit` ≥2** | **✅ 多惯习面被用到（C6 自协调的前提）** |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_blk"
TAG="BK6"
LOG=_w2_r581_blkarm.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ★ F 的配置（逐字照抄 _r581_mn64f.sh 的 BASE），只加 --pair-every 10
BASE="--N 64 --dx-nm 62.5 --steps 250 --every 5 --snap-every 50 \
  --pair-every 10 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 74 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6"
m=20
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")

say "=== R581-R172：C6 的直接判据量（F 配置 + --pair-every 10，250 步）==="
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存：available=${avail} MB（N=64/`nv`=240 预计 ~2.2 GB）"
[ "$avail" -lt 3000 ] && { say "❌ 内存不足（<3 GB）⇒ 不动"; exit 3; }

if [ -d "$ROOT/dry_$TAG" ]; then
  mv "$ROOT/dry_$TAG" "$ROOT/dry_${TAG}_superseded_$(date '+%Y%m%d_%H%M%S')"
  say "旧的 dry_$TAG 已 mv 归档"
fi

say "起 $TAG（cores 12-15，setsid nohup ⇒ 不受启动器退出影响，见 P42）"
setsid nohup env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 12-15 $PY -u _bk_exp.py $BASE \
  --out "$ROOT" --tag "$TAG" --laths "$laths" \
  > "_w2_r581_blk_${TAG}.log" 2>&1 < /dev/null &
disown 2>/dev/null || true
sleep 25
for p in $(pgrep -f "_bk_exp.py.*--tag $TAG" 2>/dev/null); do
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  say "  pid=$p RSS=${rss}MB 在跑 ✓"
done
say "（若上面没有 pid ⇒ 它没起来，查 _w2_r581_blk_${TAG}.log）"
say "=== 已起；~1.5–2 h 后回来看 ==="
