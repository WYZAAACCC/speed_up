#!/bin/bash
# _t5_readlog.sh --- 读持久判定日志（设计好的接口，非轮询作业）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 自动判定日志（末尾 14 行）════'
tail -14 _w2_t5_auto_judge.log 2>/dev/null | sed 's/^/  /'
echo
echo '════ 两臂末步与关键计数 ════'
for t in t5H3 t5V2; do
  printf '  %-5s 末步=%-6s 事件=%-4s fresh=%-3s 被拒=%s\n' "$t" \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(grep -c 'athermal 形核' _w2_t5_short_$t.log 2>/dev/null)" \
    "$(grep -c '模式 \*\*fresh\*\*' _w2_t5_short_$t.log 2>/dev/null)" \
    "$(grep -c '被引擎拒' _w2_t5_short_$t.log 2>/dev/null)"
done
echo
echo '════ 判据④ 的签名（nf2）—— **按列名读**（s194 修：原先取"最后一列"是错的）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import csv
for t in ('t5H3', 't5V2'):
    try:
        rows = list(csv.DictReader(open('_exp/_bk_t5/dry_%s/series.csv' % t, newline='')))
    except Exception as e:
        print('  %-5s ⚠ 读不到（%s）' % (t, e)); continue
    v = None; st = None
    for r in reversed(rows):
        s = (r.get('nf2') or '').strip()
        if s not in ('', 'nan'):
            v = s; st = r.get('step'); break
    nz = [r.get('step') for r in rows
          if (r.get('nf2') or '').strip() not in ('', 'nan') and float(r['nf2']) > 0]
    print('  %-5s 末行 nf2 = %-8s (step %s)   **nf2>0 的首次 step = %s**'
          % (t, v, st, (nz[0] if nz else '（尚无）')))
    print('         ⇒ 判据④ %s' % ('**已出现签名**' if nz else '未出现（尺度 ~2580 步）'))
PYEOF
