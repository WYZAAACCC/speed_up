#!/bin/bash
# _r579_wait.sh --- 等一会儿再看各道结果（避免反复手工 poll）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
sleep "${1:-300}"
echo "=== T（§3 六臂 A/B）==="
tail -22 _w2_r579_par_T.log 2>/dev/null
echo
echo "=== N（N=160 标度）==="
tail -18 _w2_r579_n160.log 2>/dev/null || echo "  (还没出)"
echo
echo "=== M 各道 ==="
for f in MA1 MA2 MB1 MB2 MC1 MC2 MD1 MD2 MD3 MD4; do
  L="_w2_r579_par_$f.log"
  if [ -f "$L" ]; then printf '%-4s %s\n' "$f" "$(tail -1 "$L" | cut -c1-110)"; fi
done
echo
echo "=== 进程 ==="
ps -eo pcpu,etimes,comm --sort=-pcpu | head -6
free -m | head -2
