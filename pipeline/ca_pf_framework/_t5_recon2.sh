#!/bin/bash
# _t5_recon2.sh --- 侦察第二批：简化审计 / 驱动力实现 / 预算
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① abA 的盒尺寸 / 历时 / 可用快照 ════'
$PY - <<'PYEOF'
import json, os, glob
m = json.load(open('_exp/_bk_mb/dry_abA/meta.json', encoding='utf-8'))
print('  顶层 L = %s nm = %.2f µm' % (m.get('L'), float(m.get('L', 0))/1000))
print('  N=%s dx=%s nm ⇒ N*dx = %.0f nm = %.2f µm'
      % (m.get('N'), m.get('dx_nm'), m['N']*m['dx_nm'], m['N']*m['dx_nm']/1000))
d = '_exp/_bk_mb/dry_abA'
print('  目录文件：')
for f in sorted(os.listdir(d)):
    sz = os.path.getsize(os.path.join(d, f))/1048576.0
    print('    %-26s %9.2f MB' % (f, sz))
snaps = sorted(glob.glob(d + '/snap_*.npz'))
print('  快照数 = %d：%s' % (len(snaps), [os.path.basename(s) for s in snaps][:10]))
PYEOF
echo
echo '════ ② 已有的简化审计文档 ════'
ls -la R581_SIMPLIFICATION_AUDIT.md 2>/dev/null | sed 's/^/  /'
[ -f R581_SIMPLIFICATION_AUDIT.md ] && { echo '  ── 章节 ──'; grep -n '^#' R581_SIMPLIFICATION_AUDIT.md | head -26 | sed 's/^/    /'; }
echo
echo '════ ③ ★ 驱动力到底怎么算的（用户点名的那一类简化）════'
echo '  ── 含 dG / df / T_of_t / dG_of_T 的定义点 ──'
grep -n 'def dG_of_T\|def T_of_t\|def dG_max\|dG_of_T(\|T_of_t(' _bk_exp.py windowB_surface.py 2>/dev/null \
  | head -18 | cut -c1-118 | sed 's/^/    /'
echo
echo '  ── "把 dG 当常数"的可疑写法（赋一次、之后不更新）──'
grep -n 'df *= *np\.\|df *= *float\|dG *= *' _bk_exp.py 2>/dev/null | head -20 | cut -c1-118 | sed 's/^/    /'
echo
echo '════ ④ 内存与时间预算（N=160 可行性）════'
free -m | sed -n '1,3p' | sed 's/^/  /'
echo '  ── 核数 ──'; nproc | sed 's/^/    /'
echo '  ── 归档里 N=160 的臂（用于内存/时长参考）──'
for t in p2_b3 p2_b5 p2_b5ov p2_b5ps p2_m12ov; do
  d=$(ls -d _exp/*/dry_$t 2>/dev/null | head -1)
  [ -n "$d" ] && printf '    %-10s %s  series %s 行  末步 %s\n' "$t" "$d" \
    "$(wc -l < "$d/series.csv" 2>/dev/null)" "$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)"
done
echo
echo '════ ⑤ 形核 seed 旋钮（判据①"随机形核"的关键）════'
grep -n 'seed' _bk_exp.py 2>/dev/null | grep -i 'add_argument\|eng_seed\|nuc.*seed' | head -10 | cut -c1-118 | sed 's/^/    /'
grep -n 'def nuc_cfg' windowB_surface.py | sed 's/^/    /'
