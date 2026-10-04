#!/bin/bash
# 验证 s301c：SEED_CLEAN=1（env 门控，与 self._nuc 无关）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10CL3
LOG=_w2_t10_cl3.log
: > "$LOG"
{
  echo "════ s301c 验证（SEED_CLEAN=1）$(date '+%m-%d %H:%M:%S') ════"
  echo -n "  文件里 getattr(self,'_nuc',None) 出现次数（合法，含 periodic_seed）："
  grep -c "getattr(self, '_nuc', None)" windowB_surface.py
  echo -n "  env 门控 SEED_CLEAN 出现："
  grep -c "SEED_CLEAN" windowB_surface.py
  echo -n "  独有成功串 [SEEDCLEAN] 出现："
  grep -c "\[SEEDCLEAN\]" windowB_surface.py
} >> "$LOG"
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "❌ $f 语法错" >> "$LOG"; exit 1; }
done
echo "  ✅ 语法 OK" >> "$LOG"

SEED_CLEAN=1 setsid $PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 2 --m 22 --B 1 \
    --steps 5 --every 1 --snap-every 1 --pair-every 1000 --ckpt-every 0 \
    --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --nuc-occ-guard 1 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 20 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（SEED_CLEAN=1）" >> "$LOG"
for i in $(seq 1 25); do
  sleep 60
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  NS=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)
  NC=$(grep -ac '\[SEEDCLEAN\]' _w2_t5_short_$TAG.log 2>/dev/null)
  if [ -z "$P" ]; then
    echo "  [$((i*60))s] 结束（快照=$NS SEEDCLEAN行=$NC）" >> "$LOG"
    grep -aE 'Traceback|error:' _w2_t5_short_$TAG.log 2>/dev/null | tail -2 | sed 's/^/    /' >> "$LOG"
    break
  fi
  echo "  [$((i*60))s] 快照=$NS SEEDCLEAN行=$NC" >> "$LOG"
done
{
  echo ""
  echo "════ ★ 独有成功串前 12 行 ════"
  grep -a '\[SEEDCLEAN\]' _w2_t5_short_$TAG.log 2>/dev/null | head -12
  echo "  SEEDCLEAN 行数 = $(grep -ac '\[SEEDCLEAN\]' _w2_t5_short_$TAG.log 2>/dev/null)"
  echo ""
  echo "════ 逐帧（SEED_CLEAN=1）════"
  $PY _t10_frame.py $TAG 5 2>&1 | head -12
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
cat "$LOG"
