#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
sleep "${1:-240}"
echo "=== P1 后的 N=160 onfly 内存复测 ==="
for f in f64n4 f64n8 f32n4 f32n8; do
  L="_w2_r580_mem_$f.log"
  printf '%-6s %s\n' "$f" "$(tail -1 "$L" 2>/dev/null | cut -c1-110)"
done
echo
echo "=== 进程 ==="
ps -eo pid,args | grep '[_]r579_mem160' | head -4
echo
echo "=== 汇总（含 c 的 P1 增量）==="
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import json, os
HERE = '.'
N3 = 160 ** 3
CELL = N3 / 2 ** 20
BUD = 22528.0
def rd(prec, nv, mode):
    for p in ('_w2_r579_one_%s_nv%d_%s.json' % (prec, nv, mode),
              '_w2_r579_one_%s_nv%d.json' % (prec, nv)):
        if os.path.exists(p) and (mode == 'materialized' or '_onfly' in p):
            with open(p, encoding='utf-8') as fh:
                return json.load(fh)
    return None
NEED = 781
print('  %-18s %-10s %-11s %-11s %-8s %s' % ('配置', 'a(B/胞)', '每nv(MB)', '固定(MB)', 'nv_max', 'vs 781'))
print('  ' + '-' * 78)
for prec in ('f64', 'f32'):
    for mode in ('materialized', 'onfly'):
        m4, m8 = rd(prec, 4, mode), rd(prec, 8, mode)
        if m4 is None or m8 is None:
            print('  %-18s （缺数据）' % ('%s/%s' % (mode, prec))); continue
        a = (m8['total'] - m4['total']) / (4.0 * N3)
        c = (m4['total'] - 4.0 * a * N3) / N3
        per, fix = a * CELL, c * CELL
        nvm = max(int((BUD - fix) / per), 0)
        print('  %-18s %-10.5f %-11.2f %-11.1f %-8d %s'
              % ('%s + %s' % (mode, prec), a, per, fix, nvm,
                 '✅ 够' if nvm >= NEED else '❌ 差 %.2f×' % (NEED / max(nvm, 1))))
PYEOF
