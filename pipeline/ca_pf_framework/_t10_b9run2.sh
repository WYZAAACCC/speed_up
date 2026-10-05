#!/bin/bash
# _t10_b9run2.sh --- ★ 修正：用 `--B 9`（启动器把 --B 透传成 --nuc-block-target）
#   前情：v1 用 `--nuc-block-target 9` ⇒ 启动器不声明该参数 ⇒ 立即崩（unrecognized arguments）
#   依据：总根数 = B · n(T_end) = 3 × 23 = 69（当前上限）；目标 200+ 且 ≤ nv=220 ⇒ **B = 9 ⇒ 9×23 = 207**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10B9
TS=$(date +%m%d_%H%M)
LOG=_w2_t10_b9.log
: > "$LOG"
{
  echo "════ B → 9（板条总数 69 → 207）修正版 $TS ════"
  echo -n "  启动器里 --B 的透传行："
  grep -n "nuc-block-target" _t5_short.py | head -2 | cut -c1-90 | tr '\n' ' '
  echo
  echo -n "  旧崩溃残留目录："; ls -d _exp/_bk_t5/dry_t10B9 2>/dev/null || echo "（无）"
  free -m | sed -n '2,3p' | sed 's/^/  /'
} >> "$LOG"
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*|*_t10_sw2.sh*) kill -9 "$P" 2>/dev/null; echo "  KILL pid=$P" >> "$LOG" ;; esac
done
sleep 5
[ -d _exp/_bk_t5/dry_t10B9 ] && mv _exp/_bk_t5/dry_t10B9 _exp/_bk_t5/dry_t10B9_crash_$TS
[ -f _w2_t10_exit.txt ] && mv _w2_t10_exit.txt _w2_t10_exit_b9v1_$TS.txt
{
  echo -n "  补丁硬门 s301c SEED_CLEAN："; awk "/SEED_CLEAN/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s304 写前掩码："; awk "/_carved = \\[j for j in range/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s304 保护跳过："; awk "/j not in _prot/{n++} END{print n+0}" windowB_surface.py
  echo -n "  s303 周期门控："; awk "/SEED_CLEAN_EVERY/{n++} END{print n+0}" _bk_exp.py
  echo -n "  s296 形核闸门："; awk "/_eta_sc \\* med > fcrit/{n++} END{print n+0}" windowB_surface.py
  echo "  ★ 预期板条总数 = 9 × 23 = 207（≤ nv = 10×22 = 220）"
} >> "$LOG"
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "❌ $f 语法错" >> "$LOG"; exit 1; }
done
echo "  ✅ 语法 OK" >> "$LOG"

SEED_CLEAN=1 SEED_CLEAN_EVERY=20 SEED_PROTECT=1 SEED_PROTECT_MIN=100 \
SEED_CARVED_DBG=1 setsid $PY _t5_short.py --tag $TAG \
    --N 160 --dx-nm 62.5 --nvar 10 --m 22 --B 9 \
    --steps 20000 --every 20 --snap-every 100 --pair-every 100 --ckpt-every 200 --ckpt-keep 2 \
    --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --nuc-occ-guard 1 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 27 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（--B 9 ⇒ --nuc-block-target 9）" >> "$LOG"
setsid nohup bash _t10_sw2.sh $TAG 28800 > /dev/null 2>&1 < /dev/null &
echo "  swap 报警已挂" >> "$LOG"
sleep 200
{
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  if [ -n "$P" ]; then
    echo "  ★ 引擎在 pid=$P 历龄=$(ps -o etime= -p $P | tr -d ' ')"
    tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-N [0-9]+|\-\-dx-nm [0-9.]+|\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-nuc-block-target [0-9]+|\-\-ed-eta [0-9.]+' | tr '\n' ' ' | sed 's/^/  开关：/'
    echo; awk '/^VmRSS|^VmSwap/{printf "  %s\n", $0}' /proc/$P/status
  else
    echo "  ⚠ 仍未找到进程"
    [ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt | sed 's/^/    exit: /'
    tail -4 _w2_t5_short_$TAG.log 2>/dev/null | tr -d '\r' | cut -c1-140 | sed 's/^/    /'
  fi
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
cat "$LOG"
