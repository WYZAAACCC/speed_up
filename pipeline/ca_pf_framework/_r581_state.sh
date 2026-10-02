#!/bin/bash
# _r581_state.sh --- 一屏看全当前运行状态（**给用户看的时间线**）
cd "$(dirname "$0")" || exit 1
NOW=$(date '+%F %T')
echo "════════════════════════════════════════════════════════════════════"
echo "  R581 运行状态 @ $NOW"
echo "════════════════════════════════════════════════════════════════════"
echo
echo '── ① 正在跑的臂（worker，按 RSS）──'
ps -eo pid,rss,args --no-headers 2>/dev/null | grep '_bk_exp\.py' | grep -v grep \
  | awk '{tag=""; for(i=1;i<=NF;i++) if($i=="--tag") tag=$(i+1);
          if(tag!="") printf "  %-10s pid=%-7s RSS=%.2f GB\n", tag, $1, $2/1048576}'
echo
echo '── ② 各臂走到哪一步（**读日志，不读 CSV** —— CSV 按 --every 5 写会滞后）──'
for t in p2_b5 p2_b3 p2_b5ov p2_b5ps p2_m12 p2_m12b p2_m20; do
  f="_w2_r581_p2_${t}.log"
  if [ -f "$f" ]; then
    last=$(grep -o '\[ *[0-9]*\]' "$f" 2>/dev/null | tail -1 | tr -d '[] ')
    mod=$(date -r "$f" '+%H:%M:%S')
    printf '  %-10s 末 step=%-6s 日志最后写入 %s\n' "$t" "${last:-?}" "$mod"
  fi
done
echo
echo '── ③ 队列（两级）──'
echo "  _r581_mqueue.sh  进程=$(ps -eo args --no-headers 2>/dev/null | grep '_r581_mqueue\.sh' | grep -vc grep)"
echo "  _r581_mqueue2.sh 进程=$(ps -eo args --no-headers 2>/dev/null | grep '_r581_mqueue2\.sh' | grep -vc grep)"
echo '  ── mqueue 日志尾 ──'
tail -2 _w2_r581_mqueue.log 2>/dev/null | sed 's/^/    /'
echo '  ── mqueue2 日志尾 ──'
tail -2 _w2_r581_mqueue2.log 2>/dev/null | sed 's/^/    /'
echo
echo '── ④ 内存与负载 ──'
free -m | sed -n '2p' | sed 's/^/  /'
awk '{printf "  loadavg 1/5/15 = %s %s %s\n", $1, $2, $3}' /proc/loadavg
echo
echo '── ⑤ 各臂产物 ──'
for t in p2_b5 p2_b3 p2_b5ov p2_b5ps p2_m12 p2_m12b p2_m20; do
  d="_exp/_bk_p2/dry_$t"
  [ -d "$d" ] || continue
  sn=$(ls "$d" 2>/dev/null | grep -c '^snap_')
  printf '  %-10s series=%-5s 快照=%-3s nuc_dbg=%s B\n' "$t" \
    "$(wc -l < "$d/series.csv" 2>/dev/null || echo 0)" "$sn" \
    "$([ -f "$d/nuc_dbg.json" ] && stat -c %s "$d/nuc_dbg.json" || echo 0)"
done
echo
echo '════════════════════════════════════════════════════════════════════'
