#!/bin/bash
# 验证 s301：与 t10DGN/t10OCC 同配置，只把 --nuc-occ-guard 设成 2
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10CLN
LOG=_w2_t10_cln.log
: > "$LOG"
echo "════ s301 连通性清理验证 $(date '+%m-%d %H:%M:%S') ════" >> "$LOG"
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "❌ $f 语法错" >> "$LOG"; exit 1; }
done
echo "  ✅ 语法 OK ；s301 helper 数 = $(awk '/def keep_largest_neg/{n++} END{print n+0}' windowB_surface.py)" >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 2 --m 22 --B 1 \
    --steps 20 --every 1 --snap-every 1 --pair-every 1000 --ckpt-every 0 \
    --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --nuc-occ-guard 2 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 20 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（--nuc-occ-guard 2）" >> "$LOG"

for i in $(seq 1 30); do
  sleep 60
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  NS=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)
  if [ -z "$P" ]; then echo "  [$((i*60))s] 结束（快照=$NS）" >> "$LOG"; break; fi
  echo "  [$((i*60))s] 快照=$NS" >> "$LOG"
done
{
  echo ""
  echo "════ 逐帧分量数（清理 ON）════"
  $PY _t10_frame.py $TAG 2>&1 | head -12
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
cat "$LOG"
