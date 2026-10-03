#!/bin/bash
# _t5_capnum.sh --- `t5N276` 的容量/目标/实际：三个数各是多少
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t5N276.log
echo '════ ① 横幅里的"板条数 / 总根数 / 容量" ════'
grep -nE '导出板条数|总根数|要真拿到|nv=|nvar|laths' "$L" 2>/dev/null | head -12 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② 判决行（实际形成几根）════'
grep -nE '判决|nslab_n 1→|nf3_col 0→|主判据' "$L" 2>/dev/null | tail -5 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ③ series.csv 末行的关键计数 ════'
tail -1 _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null | tr ',' '\n' | nl -ba | head -18 | sed 's/^/  /'
echo
echo '════ ④ 块表末行（nslab_n / nblk_sig / blk_laths）════'
awk -F, 'NR==1{for(i=1;i<=NF;i++)h[i]=$i} $0!=""{n=NF; for(i=1;i<=NF;i++) v[i]=$i; last=$1} END{}' \
  _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null >/dev/null
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import csv
rows = list(csv.DictReader(open('_exp/_bk_t5/dry_t5N276/series.csv', newline='')))
blk = [r for r in rows if (r.get('nblk_sig') or '').strip()]
print('  最后一条块表行：')
r = blk[-1] if blk else rows[-1]
for k in ('step', 'nslab_n', 'nf3_col', 'nf2', 'nblk_sig', 'n_var_sig', 'blk_laths', 'Vt'):
    if k in r:
        v = r[k]
        if k == 'Vt':
            try: v = '%.4f µm³' % (float(v) * 1e18)
            except Exception: pass
        print('     %-12s %s' % (k, v))
PYEOF
