#!/bin/bash
# _r581_ckpt_func.sh --- ★★★★★ 检查点**功能测试**：真的写出来了吗？带齐状态了吗？磁盘恒定吗？
#
# ## 三条判据（预先写死）
# | # | 判据 | 怎么算数 |
# |---|---|---|
# | F-1 | **检查点真的落盘** | `ckpt/` 下出现 `ckpt_A.npz`/`ckpt_B.npz`，且能被 `_r581_ckpt_ls.py` 读懂 |
# | F-2 | **状态带齐** | `_r581_ckpt_ls.py` 报 **缺失项 = 0**，且 `phi` 的 dtype = **float64** |
# | F-3 | **★ 滑动窗口磁盘恒定** | 跑 ≥3 个检查点周期后，`ckpt/` 的体积**不随步数增长**（A/B 只有 2 个文件） |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
OUT=_exp/_bk_ckptfunc
TAG=ckf64
LOG=_w2_r581_ckptfunc.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say '=== 检查点功能测试（N=64 / nv=240 / 40 步 / --ckpt-every 5 --ckpt-keep 2）==='
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "available=${avail} MB"
if [ -d "$OUT/dry_$TAG" ]; then
  mv "$OUT/dry_$TAG" "$OUT/dry_${TAG}_superseded_$(date '+%Y%m%d_%H%M%S')"
  say '  旧产物已 mv 归档（未删除）'
fi
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")

# ★ 与 `_r581_ckpt_measure.sh` **逐字同一条命令行**，只把 `--phi-every 1` 换成 `--ckpt-*`
timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 0-7 $PY -u _bk_exp.py \
  --N 64 --dx-nm 62.5 --steps 40 --every 20 --snap-every 20 --pair-every 50 \
  --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
  --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --reinit-dt 1e-4 --reinit-band 6.0 \
  --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4 \
  --ckpt-every 5 --ckpt-keep 2 --ckpt-atomic 1 \
  --out "$OUT" --tag "$TAG" --laths "$laths" \
  > "_w2_r581_ckptfunc_${TAG}.log" 2>&1
rc=$?
say "跑完：exit=$rc；Traceback=$(grep -c '^Traceback' "_w2_r581_ckptfunc_${TAG}.log" 2>/dev/null || echo 0)"
echo
say '── F-1：检查点真的落盘了吗 ──'
ls -la "$OUT/dry_$TAG/ckpt/" 2>/dev/null | sed 's/^/  /' || say '  ❌ **没有 ckpt/ 目录**'
echo
say '── 引擎打的检查点日志 ──'
grep '\[ckpt' "_w2_r581_ckptfunc_${TAG}.log" 2>/dev/null | tail -12 | sed 's/^/  /' || say '  （没有 [ckpt ...] 行）'
echo
say '── F-3：滑动窗口的磁盘（应恒定：A/B 只有 2 个文件）──'
printf '  ckpt/ 文件数：%s\n' "$(ls -1 "$OUT/dry_$TAG/ckpt/" 2>/dev/null | wc -l)"
printf '  ckpt/ 体积  ：%s\n' "$(du -sh "$OUT/dry_$TAG/ckpt/" 2>/dev/null | cut -f1)"
echo
say '── F-2：逐项核对状态（缺失项必须 = 0）──'
for f in "$OUT/dry_$TAG"/ckpt/ckpt_A.npz "$OUT/dry_$TAG"/ckpt/ckpt_B.npz; do
  [ -f "$f" ] || continue
  $PY _r581_ckpt_ls.py "$f" 2>&1 | tail -46 | sed 's/^/  /'
done
echo
say '── ★ 门 0 的反面：本次**传了** `--ckpt-every`，所以 `snap_*.npz` 仍应照常落盘 ──'
ls -1 "$OUT/dry_$TAG"/snap_*.npz 2>/dev/null | sed 's/^/  /'
say '=== DONE ==='
