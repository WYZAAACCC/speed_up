#!/bin/bash
# _t5_waitB12N.sh --- ★★★★★★ 等 `t5B12N` 的 `n_var_sig` 达到 ≥6，然后自动判定两臂对照
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TGT=${1:-6}; LIM=${2:-14400}; T=0
echo "  等 t5B12N（--N 100 --B 12）的 n_var_sig ≥ $TGT（最多 ${LIM} s；A 臂对照 = 3）"
while [ "$T" -lt "$LIM" ]; do
  V=$($PY - <<'PYEOF' 2>/dev/null
import csv, os
P = '_exp/_bk_t5/dry_t5B12N/series.csv'
if not os.path.exists(P):
    print(-1); raise SystemExit
rows = [r for r in csv.DictReader(open(P, newline='')) if (r.get('n_var_sig') or '').strip().isdigit()]
print(int(rows[-1]['n_var_sig']) if rows else -1)
PYEOF
)
  [ -n "$V" ] && [ "$V" -ge "$TGT" ] 2>/dev/null && { echo "  ★ n_var_sig = $V（达到 $TGT）"; break; }
  P=$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5B12N')
  [ "$P" -eq 0 ] && { echo "  ⚠ t5B12N 进程消失（n_var_sig 停在 $V）"; break; }
  sleep 120; T=$((T + 120))
done
echo "NOW = $(date '+%F %T')  等了 ${T} s"
echo
echo '════ ★★ 两臂对照（决定性）════'
$PY - <<'PYEOF'
import csv, os
print('  %-22s %-8s %-11s %-10s %-9s %-8s %s'
      % ('臂', '末步', 'n_var_sig', 'nblk_sig', 'nslab_n', 'nf2', 'blk_laths'))
for tag, lab in (('t5N276F', '--N 80 --B 3 (对照)'), ('t5B12N', '--N 100 --B 12 (修复)')):
    P = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(P):
        print('  %-22s （无数据）' % lab); continue
    rows = list(csv.DictReader(open(P, newline='')))
    br = [r for r in rows if (r.get('nblk_sig') or '').strip()]
    if not br:
        print('  %-22s （无块表行）' % lab); continue
    b = br[-1]
    print('  %-22s %-8s **%-11s** %-10s %-9s %-8s %s'
          % (lab, b['step'], b.get('n_var_sig'), b.get('nblk_sig'),
             b.get('nslab_n'), b.get('nf2'), (b.get('blk_laths') or '')[:28]))
print()
print('  ── 判据①（**预先写死**）──')
print('  * A 臂（--B 3）实测 `n_var_sig` = **3**（自协调需 **12**）;')
print('  * **B 臂 ≥6 ⇒ 变体数上升 ⇒ 自协调部分/完全成立** ⇒ 设计级根因确认 ✓;')
print('  * B 臂仍 ≈3 ⇒ 块目标未转化为变体数 ⇒ 需查 `var-rule` 在 `fresh` 里的实际选择。')
PYEOF
echo
echo '════ 判据②：`Δed` 带符号（A 臂 = −2.955e8，<0 占 100%）════'
grep -E 'Δed 带符号' _w2_t5_short_t5B12N.log 2>/dev/null | tail -3 | cut -c1-195 | sed 's/^/  /'
echo '  （为空 ⇒ 诊断还没到输出步）'
echo '════ 形核事件模式分布 ════'
for m in fresh attach stack; do
  printf '  %-7s = %s\n' "$m" "$(grep -cE "模式 \*\*$m\*\*" _w2_t5_short_t5B12N.log 2>/dev/null)"
done
echo '════ Vt 轨迹尾部 ════'
grep -E '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5B12N.log 2>/dev/null | tail -4 | cut -c1-120 | sed 's/^/  /'
