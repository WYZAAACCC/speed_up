#!/bin/bash
# _t5_recon3.sh --- 侦察第三批（跳过 n=148 个快照的清单）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① abA 概要（不列快照）════'
$PY - <<'PYEOF'
import json, os, glob, csv
m = json.load(open('_exp/_bk_mb/dry_abA/meta.json', encoding='utf-8'))
d = '_exp/_bk_mb/dry_abA'
snaps = sorted(glob.glob(d + '/snap_*.npz'))
print('  N=%d  dx=%.1f nm  ⇒ 盒 = %.2f µm' % (m['N'], m['dx_nm'], m['N']*m['dx_nm']/1000))
print('  steps=%d  快照 %d 个（每 %s 步）  最大快照 %.2f MB'
      % (m['steps'], len(snaps), m.get('snap_every'),
         max(os.path.getsize(s) for s in snaps)/1048576))
rows = list(csv.DictReader(open(d + '/series.csv', encoding='utf-8', errors='replace')))
print('  series 行数 = %d  末步 = %s' % (len(rows), rows[-1]['step']))
if 'wall_s' in rows[0]:
    w = [float(r['wall_s']) for r in rows if r.get('wall_s') not in (None, '')]
    print('  wall_s 合计 = %.0f s = %.2f h（%d 行）' % (sum(w), sum(w)/3600, len(w)))
for c in ('Vt', 'f_var', 'nslab_n1', 'nf3', 'nf2'):
    if c in rows[0]:
        print('  末值 %-10s = %s' % (c, rows[-1].get(c)))
PYEOF
echo
echo '════ ② 简化审计文档 ════'
ls -la R581_SIMPLIFICATION_AUDIT.md 2>/dev/null | sed 's/^/  /'
[ -f R581_SIMPLIFICATION_AUDIT.md ] && grep -n '^#' R581_SIMPLIFICATION_AUDIT.md | head -26 | sed 's/^/    /'
echo
echo '════ ③ ★ 驱动力实现（用户点名的那一类）════'
grep -n 'def dG_of_T\|def T_of_t\|def dG_max' _bk_exp.py 2>/dev/null | cut -c1-118 | sed 's/^/    /'
echo '  ── df 的赋值点（"当常数用"就藏在这里）──'
grep -n 'g\.df *=\|\.df\[' _bk_exp.py windowB_surface.py 2>/dev/null | head -16 | cut -c1-118 | sed 's/^/    /'
echo
echo '════ ④ 预算 ════'
free -m | sed -n '2p' | sed 's/^/  /'
printf '  核数 = %s\n' "$(nproc)"
echo
echo '════ ⑤ N=160 的归档臂（内存/时长参考）════'
for t in p2_b3 p2_b5 p2_b5ov p2_b5ps; do
  d=$(ls -d _exp/*/dry_$t 2>/dev/null | head -1)
  [ -n "$d" ] && printf '    %-9s %-34s 末步 %-6s\n' "$t" "$d" \
    "$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)"
done
echo
echo '════ ⑥ seed 旋钮 ════'
grep -n "add_argument('--eng-seed\|add_argument('--nuc-seed\|add_argument('--seed" _bk_exp.py 2>/dev/null | cut -c1-118 | sed 's/^/    /'
grep -n 'def nuc_cfg' windowB_surface.py | cut -c1-118 | sed 's/^/    /'
