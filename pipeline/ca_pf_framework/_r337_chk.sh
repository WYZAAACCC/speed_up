#!/usr/bin/env bash
# _r337_chk.sh -- 统一进度/存活检查
D=/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_mb
R=/mnt/f/speed_up/pipeline/ca_pf_framework
for n in dry_saSet2P0 dry_saSet2F2P0 dry_near200 dry_mid200 dry_far200; do
  last=$(ls "$D/$n"/snap_*.npz 2>/dev/null | tail -1)
  cnt=$(ls "$D/$n"/snap_*.npz 2>/dev/null | wc -l)
  printf '%-18s nsnap=%-4s last=%s\n' "$n" "$cnt" "${last##*/}"
done
echo "运行中的 _bk_exp 进程数: $(pgrep -c -f '_bk_exp[.]py' || echo 0)"
echo "--- _w2_r280.log tail ---"
tail -4 "$R/_w2_r280.log" 2>&1
echo "--- _w2_r322.log tail ---"
tail -4 "$R/_w2_r322.log" 2>&1
free -g | head -2
uptime
