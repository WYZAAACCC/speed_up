#!/bin/bash
# _t5_res.sh --- 资源与进度检查（决定能否再起剂量-响应 A/B）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
bash -n _t5_ab_dose.sh && echo '  ✅ 剂量-响应 A/B 语法 OK（已备好）'
echo
free -m | sed -n 2p | sed 's/^/  内存: /'
echo -n '  bk_exp 进程数 = '; ps -eo args --no-headers | grep -c '[_]bk_exp.py'
echo
echo '── 四臂 A/B 进度 ──'
for t in A B C D; do
  printf '  t5AB_%-2s 末步=%-6s\n' "$t" "$(tail -1 _exp/_bk_t5/dry_t5AB_$t/series.csv 2>/dev/null | cut -d, -f1)"
done
echo '── t5V2 ──'
tail -1 _exp/_bk_t5/dry_t5V2/series.csv 2>/dev/null | cut -d, -f1 | sed 's/^/  末步=/'
echo
echo '── 监控 ──'
ps -eo pid,etime,args --no-headers | grep '[p]ython _t5_armon' | cut -c1-60 | sed 's/^/  /'
