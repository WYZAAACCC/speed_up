#!/bin/bash
# _t5_bigstatus.sh --- ★★★★★ 新大实验（`t5N276F`）的完整现状
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5N276F
echo "NOW = $(date '+%F %T')"
echo '════ ① 存活与进度 ════'
printf '  引擎进程 = %s   末步 = %s   快照 = %s   ckpt = %s\n' \
  "$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- "--tag $TAG")" \
  "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(ls -1 _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)" \
  "$(ls -1 _exp/_bk_t5/dry_$TAG/ckpt/*.npz 2>/dev/null | wc -l)"
echo
echo '════ ② 是否已结束（日志尾部）════'
grep -E '准静态钟|提前结束|走到 step|exit=' _w2_t5_short_$TAG.log 2>/dev/null | tail -3 | cut -c1-155 | sed 's/^/  /'
echo
echo '════ ③ 块表演进（全部块表行）════'
$PY - <<'PYEOF'
import csv
b=[r for r in csv.DictReader(open('_exp/_bk_t5/dry_t5N276F/series.csv',newline='')) if (r.get('nblk_sig') or '').strip()]
for r in b:
    print('  step %-6s nslab_n=%-4s nf3_col=%-4s nf2=%-6s nblk_sig=%-3s n_var_sig=%-3s blk_laths=%s'
          %(r['step'],r.get('nslab_n'),r.get('nf3_col'),r.get('nf2'),r.get('nblk_sig'),
            r.get('n_var_sig'),(r.get('blk_laths') or '')[:24]))
PYEOF
echo
echo '════ ④ 最新板条状态（活跃场数 / 占比 / 长宽比）════'
grep -E "\[$TAG\]" _w2_t5_lathmon.log 2>/dev/null | sort -u | tail -4 | cut -c1-178 | sed 's/^/  /'
echo
echo '════ ⑤ 形核账目 ════'
$PY - <<'PYEOF'
import os
from collections import Counter
L='_w2_t5_short_t5N276F.log'
ev=[]
if os.path.exists(L):
    import re
    RX=re.compile(r'@ step (\d+)：T=([\d.]+) K.*?场 (\d+)（累计 (\d+)/(\d+)；模式 \*\*([a-z]+)\*\*')
    for line in open(L,errors='ignore'):
        m=RX.search(line)
        if m: ev.append((int(m.group(1)),float(m.group(2)),int(m.group(3)),m.group(6)))
f=[e[2] for e in ev]
print('  事件 %d ｜ 不同场 %d ｜ **唯一性 = %.2f**（修复前 0.56）'%(len(ev),len(set(f)),len(set(f))/len(ev) if ev else 0))
print('  模式分布 = %s'%dict(Counter(e[3] for e in ev)))
print('  最后事件：step %s T=%.1f 场 %s 模式 %s'%(ev[-1][0],ev[-1][1],ev[-1][2],ev[-1][3]) if ev else '  （无）')
PYEOF
echo
echo '════ ⑥ 步对齐对照（vs 修复前 t5N276 的同 step）════'
$PY _t5_samecmp.py 600,1000,1400,1800,2160 t5N276,t5N276F 2>&1 | sed -n '3,11p'
echo
free -m | sed -n 2p | sed 's/^/  内存: /'
