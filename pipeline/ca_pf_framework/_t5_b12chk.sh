#!/bin/bash
# _t5_b12chk.sh --- ★★★★★★ 读 `--B 12` 实验的早期判据（核心：n_var_sig 是否上升）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5B12
echo "NOW = $(date '+%F %T')"
printf '  进程 = %s ｜ 末步 = %s ｜ 快照 = %s\n' \
  "$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- "--tag $TAG")" \
  "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(ls -1 _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)"
echo
echo '════ ★ 判据①：`n_var_sig`（变体数）—— A 臂(--B 3) 末值是 3，目标 →12 ════'
$PY - <<'PYEOF'
import csv, os
for tag, lab in (('t5B12', '--B 12 (修复)'), ('t5N276F', '--B 3 (对照)')):
    P = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(P):
        print('  %-16s （无数据）' % lab); continue
    rows = [r for r in csv.DictReader(open(P, newline='')) if (r.get('nblk_sig') or '').strip()]
    if not rows:
        print('  %-16s （还没有块表行）' % lab); continue
    print('  ── %s ──' % lab)
    for r in rows[-4:]:
        print('     step %-6s nslab_n=%-4s **n_var_sig=%s**  nblk_sig=%-4s nf2=%-6s blk_laths=%s'
              % (r['step'], r.get('nslab_n'), r.get('n_var_sig'), r.get('nblk_sig'),
                 r.get('nf2'), (r.get('blk_laths') or '')[:26]))
    ks = [int(r['n_var_sig']) for r in rows if (r.get('n_var_sig') or '').strip().isdigit()]
    if ks:
        print('     ⇒ **n_var_sig 末值 = %d**' % ks[-1])
PYEOF
echo
echo '════ 判据②：`Δed` 带符号（自协调是否生效）════'
grep -E 'Δed 带符号' _w2_t5_short_$TAG.log 2>/dev/null | tail -4 | cut -c1-190 | sed 's/^/  /'
echo '  ── 对照：A 臂（--B 3）的 F1 三项 ──'
grep -A1 'F1 含母相' _w2_t5_short_t5N276F.log 2>/dev/null | tail -2 | cut -c1-180 | sed 's/^/  /'
echo
echo '════ 判据③：逐场体积是否还在流失（Vt 轨迹 + 是否下降）════'
grep -E '^\s*\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -6 | cut -c1-130 | sed 's/^/  /'
echo
echo '════ 形核事件模式分布（fresh 是否变多）════'
for m in fresh attach stack; do
  printf '  %-7s = %s\n' "$m" "$(grep -cE "模式 \*\*$m\*\*" _w2_t5_short_$TAG.log 2>/dev/null)"
done
