#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== cln11（athermal 形核臂，6124 步）'
tail -1 _exp/_bk_closed/dry_cln11/series.csv | cut -d, -f1-3
grep -cE 'athermal 形核' _w2_cln11*.log 2>/dev/null || true
ls _w2_*cln11* 2>/dev/null
echo
echo '=== cln11 的 11 次形核事件（若有落盘）'
[ -f _exp/_bk_closed/dry_cln11/nuc_dbg.json ] && /root/miniconda3/envs/ml/bin/python -c "
import json;d=json.load(open('_exp/_bk_closed/dry_cln11/nuc_dbg.json'));print(json.dumps(d,ensure_ascii=False)[:800])"
echo
echo '=== F 盘数据总量与剩余空间'
du -sh _exp 2>/dev/null
df -h /mnt/f | tail -1
echo
echo '=== 进程'
ps -eo pcpu,etimes,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | awk '{printf "%5s%% %6ss %s %s %s\n",$1,$2,$4,$5,$6}'
