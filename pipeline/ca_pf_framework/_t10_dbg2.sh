#!/bin/bash
# _t10_dbg2.sh --- 带 SEED_DBG=1 的短诊断：数清「同一个场被播了几次」+ 探针回滚是否干净
#   配置与 t10DGN 相同（N=160、nv=2×22=44、B=1、snap-every 1、steps 20），只多 SEED_DBG=1
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10DBG
LOG=_w2_t10_dbg2.log
: > "$LOG"
echo "════ SEED_DBG=1 短诊断 $(date '+%m-%d %H:%M:%S') ════" >> "$LOG"
free -m | sed -n '2,3p' | sed 's/^/  /' >> "$LOG"

for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "❌ $f 语法错" >> "$LOG"; exit 1; }
done
echo "  ✅ 语法 OK" >> "$LOG"
echo -n "  s299 门控数（应 2）：" >> "$LOG"
awk "/SEED_DBG/{n++} END{print n+0}" windowB_surface.py >> "$LOG"

SEED_DBG=1 setsid $PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 2 --m 22 --B 1 \
    --steps 20 --every 1 --snap-every 1 --pair-every 1000 --ckpt-every 0 \
    --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 20 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（SEED_DBG=1）" >> "$LOG"

# 盯守至进程结束
for i in $(seq 1 60); do
  sleep 60
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  NS=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)
  if [ -z "$P" ]; then
    echo "  [$((i*60))s] ⚠ 结束（快照=$NS）" >> "$LOG"; break
  fi
  echo "  [$((i*60))s] 快照=$NS 运行中" >> "$LOG"
done

{
  echo ""
  echo "════ SEEDDBG 记账（按场号统计调用次数）════"
  grep -a '\[SEEDDBG\]' _w2_t5_short_$TAG.log 2>/dev/null | head -60
  echo ""
  echo "  调用总次数 = $(grep -ac '\[SEEDDBG\]' _w2_t5_short_$TAG.log 2>/dev/null)"
  echo "  按场号（k=）计数，>1 的场："
  grep -a '\[SEEDDBG\]' _w2_t5_short_$TAG.log 2>/dev/null \
    | grep -oE 'k=[0-9]+' | sort | uniq -c | awk '$1>1{print "    "$0}'
  echo "  undo=1（探针）次数 = $(grep -a '\[SEEDDBG\]' _w2_t5_short_$TAG.log 2>/dev/null | grep -c 'undo=1')"
  echo ""
  echo "════ 逐帧分量数（与 t10DGN 对照，验证记账未改数值）════"
  $PY _t10_frame.py $TAG 2>&1 | tail -8
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
cat "$LOG"
