#!/bin/bash
# _t5_b12now.sh --- 读 t5B12 当前进度与块表（n_var_sig）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B12' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
echo '── 末步 / Vt 行数 ──'
printf '  末步 = %s\n' "$(tail -1 _exp/_bk_t5/dry_t5B12/series.csv 2>/dev/null | cut -d, -f1)"
printf '  Vt 行数 = %s\n' "$(grep -cE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5B12.log 2>/dev/null)"
echo '── 块表（n_var_sig = 判据①）──'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import csv, os
for tag in ('t5B12', 't5N276F'):
    P = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(P):
        print('  %s （无数据）' % tag); continue
    rows = [r for r in csv.DictReader(open(P, newline='')) if (r.get('nblk_sig') or '').strip()]
    print('  ── %s：块表 %d 行 ──' % (tag, len(rows)))
    for r in rows[-3:]:
        print('     step %-6s nslab_n=%-4s **n_var_sig=%s**  nblk_sig=%-4s blk_laths=%s'
              % (r['step'], r.get('nslab_n'), r.get('n_var_sig'), r.get('nblk_sig'),
                 (r.get('blk_laths') or '')[:28]))
PYEOF
echo '── 形核事件模式分布 ──'
for m in fresh attach stack; do
  printf '  %-7s = %s\n' "$m" "$(grep -cE "模式 \*\*$m\*\*" _w2_t5_short_t5B12.log 2>/dev/null)"
done
echo '── 内存 ──'
free -m | sed -n 2p | sed 's/^/  /'
