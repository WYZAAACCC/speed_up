#!/bin/bash
# _t10_fix_run.sh --- ★ 生产配置 + s301c 修复（SEED_CLEAN=1 + 占用守卫），重跑 10 µm 盒
#   与 t10E253 那跑**只差**：SEED_CLEAN=1、--nuc-occ-guard 1
#   预登记判据 J1-J5（承 R601 与 _t10_eta253.sh，**不得放宽**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10FIX
LOG=_w2_t10_fix.log
TS=$(date +%m%d_%H%M)
: > "$LOG"
{
  echo "════ ★ 生产重跑（含 s301c 播种清理）$TS ════"
  free -m | sed -n '2,3p' | sed 's/^/  /'
} >> "$LOG"

# 清掉抢内存的
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in
    *bk_exp.py*|*_t10_swapalert*.sh*|*_t10_auto*.sh*|*_t10_cl3.sh*|*_t10_nosc.sh*)
      kill -9 "$P" 2>/dev/null; echo "  KILL pid=$P" >> "$LOG" ;;
  esac
done
sleep 5

# 补丁硬门
{
  echo -n "  s300 occ_guard cfg："; awk "/occ_guard=bool\(occ_guard\)/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s301c SEED_CLEAN 门控："; awk "/SEED_CLEAN/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s301c 成功串："; awk "/\[SEEDCLEAN\]/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s296 形核闸门："; awk "/_eta_sc \* med > fcrit/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s291/s292/s293："
  awk '/^ *if _ev or not _burst_on:$/{a++} /while _do_try and n_ath_tgt < _tgt/{b++} /_fresh_now = \(n_fresh_ok < int\(_Bt\)\)/{c++} END{printf "%d/%d/%d\n", a+0,b+0,c+0}' _bk_exp.py
} >> "$LOG"
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "❌ $f 语法错" >> "$LOG"; exit 1; }
done
echo "  ✅ 语法 OK" >> "$LOG"

[ -f _w2_t10_exit.txt ] && mv _w2_t10_exit.txt _w2_t10_exit_prev_$TS.txt
SEED_CLEAN=1 setsid $PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 10 --m 22 --B 3 \
    --steps 20000 --every 20 --snap-every 100 --pair-every 100 --ckpt-every 200 --ckpt-keep 2 \
    --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --nuc-occ-guard 1 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 27 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（SEED_CLEAN=1 + --nuc-occ-guard 1）" >> "$LOG"

# swap 报警 + 自动守望改指向新 tag
sed "s/^TAG=t10N160/TAG=$TAG/" _t10_swapalert.sh > _t10_sw_fix.sh
sed "s/_w2_t10_swapalert.log/_w2_t10_swapfix.log/" -i _t10_sw_fix.sh
setsid nohup bash _t10_sw_fix.sh 28800 20 > /dev/null 2>&1 < /dev/null &
echo "  swap 报警已挂（指向 $TAG）" >> "$LOG"

sleep 100
{
  echo "  ── 100 s 后复验 ──"
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  if [ -n "$P" ]; then
    echo "    pid=$P 历龄=$(ps -o etime= -p $P | tr -d ' ')"
    echo -n "    ★ 关键开关："
    tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-ed-eta [0-9.]+|\-\-nuc-occ-guard [0-9]+|\-\-burst-km [0-9]+|\-\-nvar [0-9]+|\-\-m [0-9]+' | tr '\n' ' '
    echo
    awk '/^VmRSS|^VmSwap/{printf "    %s\n", $0}' /proc/$P/status
  else echo "    ⚠ 未找到进程"; fi
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
cat "$LOG"
