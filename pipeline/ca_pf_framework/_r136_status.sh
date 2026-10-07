#!/bin/bash
# _r136_status.sh —— R132（选支对照）/ R135（PAIR 几何）/ R115（保面对照）状态
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "现在：$(date '+%F %T')"
N=$(pgrep -f '_bk_exp[.]py' 2>/dev/null | wc -l)
echo "_bk_exp 进程数：$N"
free -g | awk 'NR==2{printf "内存：%s GB available\n", $7}'
echo
echo "--- R132 选支对照（dry_swapinv）---"
tail -2 _w2_r132_swapinv.log 2>/dev/null | cut -c1-120
echo
echo "--- R115 保面对照（dry_saOddFp0）---"
tail -1 _w2_r115_saOddFp0.log 2>/dev/null | cut -c1-120
echo
echo "--- R135 PAIR 几何 ---"
tail -6 _w2_r135_run.log 2>/dev/null
echo
echo "--- R135 各臂 step0 ---"
$PY - <<'PY'
import csv, os, json
for t in ('pA', 'pB', 'pC', 'pD', 'pE', 'pF'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    mj = '_exp/_bk_mb/dry_%s/meta.json' % t
    if not os.path.exists(p):
        e = ''
        L = '_w2_r135_%s.log' % t
        if os.path.exists(L):
            for line in open(L, encoding='utf-8', errors='replace'):
                if 'exceeds domain' in line:
                    e = '崩：种子超域'
                    break
        print('  %-4s %s' % (t, e or '（未跑/无数据）'))
        continue
    rs = list(csv.DictReader(open(p)))
    ea = (json.load(open(mj)).get('exp_args', {}) or {}) if os.path.exists(mj) else {}
    print('  %-4s N=%-4s L=%-6s W=%-5s T=%-5s gap=%-6s nf2(0)=%-6s nblk=%-3s %s'
          % (t, ea.get('N'), ea.get('plate_L'), ea.get('plate_W'),
             ea.get('plate_T'), ea.get('block_gap_nm'),
             rs[0].get('nf2'), rs[0].get('nblk_sig'),
             '✅ 分离' if str(rs[0].get('nf2')) == '0' else '❌'))
PY
