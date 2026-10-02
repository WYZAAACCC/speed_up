#!/bin/bash
# _r581_ckpt_measure.sh --- ★★★★★★ **实测完整 φ 的检查点成本**（含"未活跃场是常数 1e3"的压缩红利）
#
# 目的：用户问"能不能原生精度续跑"。**判决的关键数字是：存完整 φ 每段要多少 MB/GB。**
# 做法：跑一条**短臂**（N=64、30 步、`--phi-every 1`）⇒ 拿到**真实**的完整 φ ⇒ 量落盘大小。
# 为什么 N=64 够：**活跃场数**与压缩红利主要由物理决定（与 N 无关），
#   而体量按 N³ 缩放 ⇒ **量到 N=64 的绝对值就能外推 N=160**（×15.6）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
OUT=_exp/_bk_ckpt
TAG=ckm64
LOG=_w2_r581_ckptm.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say "=== 实测：完整 φ 的检查点成本（N=64 / nv=240 / 30 步 / --phi-every 1）==="
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "available=${avail} MB"
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")
[ -d "$OUT/dry_$TAG" ] && mv "$OUT/dry_$TAG" "$OUT/dry_${TAG}_superseded_$(date '+%Y%m%d_%H%M%S')"

timeout 1800 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 0-7 $PY -u _bk_exp.py \
  --N 64 --dx-nm 62.5 --steps 30 --every 5 --snap-every 10 --pair-every 50 \
  --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
  --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --reinit-dt 1e-4 --reinit-band 6.0 \
  --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4 \
  --phi-every 1 \
  --out "$OUT" --tag "$TAG" --laths "$laths" \
  > "_w2_r581_ckptm_${TAG}.log" 2>&1
say "跑完：exit=$?；Traceback=$(grep -c '^Traceback' "_w2_r581_ckptm_${TAG}.log" 2>/dev/null || echo 0)"

say "── 快照文件与大小 ──"
ls -la "$OUT/dry_$TAG"/snap_*.npz 2>/dev/null | awk '{printf "  %s  %.2f MB\n", $9, $5/1048576}' | sed 's|.*/||'
say "── 总计 ──"
du -sh "$OUT/dry_$TAG" 2>/dev/null | sed 's/^/  /'
