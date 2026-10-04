#!/bin/bash
# _t10_verify_occ.sh --- 验证 s300 占用守卫：同配置（对照 t10DGN）加 --nuc-occ-guard 1
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10OCC
LOG=_w2_t10_occ.log
: > "$LOG"
echo "════ s300 占用守卫验证 $(date '+%m-%d %H:%M:%S') ════" >> "$LOG"
free -m | sed -n '2,3p' | sed 's/^/  /' >> "$LOG"

for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "❌ $f 语法错" >> "$LOG"; exit 1; }
done
{
  echo "  ✅ 语法 OK"
  echo -n "  s300 门控（应 1）："; awk "/occ_guard', False/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s299 SEED_DBG 门控（应 2）："; awk "/SEED_DBG/{n++} END{print n+0}" windowB_surface.py
} >> "$LOG"

# 与 t10DGN **只差** --nuc-occ-guard 1（并带 SEED_DBG=1 复核"没有场被真放两次"）
SEED_DBG=1 setsid $PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 2 --m 22 --B 1 \
    --steps 20 --every 1 --snap-every 1 --pair-every 1000 --ckpt-every 0 \
    --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --nuc-occ-guard 1 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 20 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（--nuc-occ-guard 1）" >> "$LOG"

for i in $(seq 1 40); do
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
  echo "════ 逐帧分量数（守卫 ON）════"
  $PY _t10_frame.py $TAG 2>&1 | head -12
  echo ""
  echo "════ SEEDDBG：是否还有「同一场被真放两次」════"
  echo "  调用总数 = $(grep -ac '\[SEEDDBG\]' _w2_t5_short_$TAG.log 2>/dev/null)"
  echo "  ★ 按场号计数 >1 的（undo=0 真放）："
  grep -a '\[SEEDDBG\]' _w2_t5_short_$TAG.log 2>/dev/null | grep 'undo=0' \
    | grep -oE 'k=[0-9]+' | sort | uniq -c | awk '$1>1{print "      "$0}'
  echo "  ★ 按场号计数 >1 的（含探针，全部）："
  grep -a '\[SEEDDBG\]' _w2_t5_short_$TAG.log 2>/dev/null \
    | grep -oE 'k=[0-9]+' | sort | uniq -c | awk '$1>1{print "      "$0}'
  echo "  形核事件数 = $(grep -ac 'athermal 形核' _w2_t5_short_$TAG.log 2>/dev/null)"
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
cat "$LOG"
