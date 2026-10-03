#!/bin/bash
# _t5_two_arms.sh --- 两条臂的当前状态（一行式，避免 PowerShell 引号问题）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
for t in t5N276 t5NR; do
  ST=$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)
  NS=$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | awk -F, '{print $9}')
  NB=$(awk -F, 'NR==1{for(i=1;i<=NF;i++) if($i=="nblk_sig") c=i; next} $c!=""{v=$c} END{print v+0}' \
       _exp/_bk_t5/dry_$t/series.csv 2>/dev/null)
  NV=$(awk -F, 'NR==1{for(i=1;i<=NF;i++) if($i=="n_var_sig") c=i; next} $c!=""{v=$c} END{print v+0}' \
       _exp/_bk_t5/dry_$t/series.csv 2>/dev/null)
  NF2=$(awk -F, 'NR==1{for(i=1;i<=NF;i++) if($i=="nf2") c=i; next} $c!=""{v=$c} END{print v+0}' \
       _exp/_bk_t5/dry_$t/series.csv 2>/dev/null)
  P=$(ps -eo args --no-headers 2>/dev/null | awk -v q="--tag $t" 'index($0,q){n++} END{print n+0}')
  printf '  %-8s 末步=%-6s nslab_n=%-4s nblk_sig=%-3s n_var_sig=%-3s nf2=%-3s 进程=%s\n' \
    "$t" "${ST:-—}" "${NS:-—}" "$NB" "$NV" "$NF2" "$P"
done
echo
echo '  t5NR 引擎日志错误计数：'
awk '/Traceback|Error|❌/{n++} END{print "    " n+0}' _w2_t5_nr_engine.log 2>/dev/null
echo
free -m | sed -n 2p | sed 's/^/  内存: /'
