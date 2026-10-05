#!/bin/bash
# _t10_prtrun.sh --- s304 验证轮：SEED_PROTECT=1 + 两级清理 + carved 记账
#   与 t10CL2 **只差** SEED_PROTECT=1 与 SEED_CARVED_DBG=1
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10PRT
TS=$(date +%m%d_%H%M)
LOG=_w2_t10_prt.log
: > "$LOG"
{
  echo "════ s304 核保护验证轮 $TS ════"
  free -m | sed -n '2,3p' | sed 's/^/  /'
} >> "$LOG"
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*|*_t10_sw2.sh*) kill -9 "$P" 2>/dev/null; echo "  KILL pid=$P" >> "$LOG" ;; esac
done
sleep 6
D=_exp/_bk_t5/dry_t10CL2
[ -d "$D" ] && mv "$D" "${D}_ok_$TS" && echo "  t10CL2 数据 → $(basename ${D}_ok_$TS)" >> "$LOG"
[ -f _w2_t10_exit.txt ] && mv _w2_t10_exit.txt _w2_t10_exit_cl2_$TS.txt
{
  echo -n "  s304 写前掩码："; awk "/_carved = \\[j for j in range/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s304 保护跳过："; awk "/j not in _prot/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s304 保护门控："; awk "/os.environ.get\\('SEED_PROTECT'\\) == '1'/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s304 carved 串："; awk "/\\[SEEDCARVED\\]/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s301c SEED_CLEAN："; awk "/SEED_CLEAN/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s303 周期门控："; awk "/SEED_CLEAN_EVERY/{n++} END{print n+0}" _bk_exp.py
  echo -n "  s296 形核闸门："; awk "/_eta_sc \\* med > fcrit/{n++} END{print n+0}" windowB_surface.py
} >> "$LOG"
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "❌ $f 语法错" >> "$LOG"; exit 1; }
done
echo "  ✅ 语法 OK" >> "$LOG"

SEED_CLEAN=1 SEED_CLEAN_EVERY=20 SEED_PROTECT=1 SEED_PROTECT_MIN=100 \
SEED_CARVED_DBG=1 setsid $PY _t5_short.py --tag $TAG \
    --N 160 --dx-nm 62.5 --nvar 10 --m 22 --B 3 \
    --steps 20000 --every 20 --snap-every 100 --pair-every 100 --ckpt-every 200 --ckpt-keep 2 \
    --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --nuc-occ-guard 1 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 27 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（SEED_PROTECT=1 + 两级清理 + carved 记账）" >> "$LOG"
setsid nohup bash _t10_sw2.sh $TAG 28800 > /dev/null 2>&1 < /dev/null &
echo "  swap 报警已挂" >> "$LOG"
sleep 110
{
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  if [ -n "$P" ]; then
    echo "  pid=$P 历龄=$(ps -o etime= -p $P | tr -d ' ')"
    tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-N [0-9]+|\-\-dx-nm [0-9.]+|\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-ed-eta [0-9.]+|\-\-nuc-occ-guard [0-9]+' | tr '\n' ' ' | sed 's/^/  开关：/'
    echo; awk '/^VmRSS|^VmSwap/{printf "  %s\n", $0}' /proc/$P/status
  else echo "  ⚠ 未找到进程"; fi
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
cat "$LOG"
