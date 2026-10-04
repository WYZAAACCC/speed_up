#!/bin/bash
# 决定性实验：关掉超临界探针，看多块是否消失（若消失 ⇒ 探针回滚是病灶）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10NSC
LOG=_w2_t10_nsc.log
: > "$LOG"
{
  echo "════ 探针 OFF 对照 $(date '+%m-%d %H:%M:%S') ════"
  echo -n "  _t5_short.py 是否透传 --nuc-supercrit："
  grep -c 'nuc-supercrit' _t5_short.py
  echo -n "  _bk_exp.py 是否有该开关："
  grep -c "add_argument('--nuc-supercrit'" _bk_exp.py
} >> "$LOG"
NS=$(grep -c 'nuc-supercrit' _t5_short.py)
if [ "$NS" -lt 1 ]; then
  # 没有透传 ⇒ 用 `--no-nucleation` 之外的等价手段不可得，直接报出来
  echo "  ⚠ _t5_short.py 未透传 --nuc-supercrit ⇒ 需要先加透传；本轮只报告这一事实" >> "$LOG"
  cat "$LOG"; exit 0
fi
setsid $PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 2 --m 22 --B 1 \
    --steps 5 --every 1 --snap-every 1 --pair-every 1000 --ckpt-every 0 \
    --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --nuc-occ-guard 1 \
    --nuc-supercrit 0 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 20 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（--nuc-supercrit 0, steps 5）" >> "$LOG"
for i in $(seq 1 25); do
  sleep 60
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  NS2=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)
  if [ -z "$P" ]; then
    echo "  [$((i*60))s] 结束（快照=$NS2）" >> "$LOG"
    grep -aE 'Traceback|Error|error:' _w2_t5_short_$TAG.log 2>/dev/null | tail -3 | sed 's/^/    /' >> "$LOG"
    break
  fi
  echo "  [$((i*60))s] 快照=$NS2" >> "$LOG"
done
{ echo ""; echo "════ 逐帧（探针 OFF）════"; $PY _t10_frame.py $TAG 5 2>&1 | head -12; } >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
cat "$LOG"
