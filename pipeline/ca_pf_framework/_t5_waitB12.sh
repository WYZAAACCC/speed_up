#!/bin/bash
# _t5_waitB12.sh --- ★★★★★★ 等 `t5B12` 的 `n_var_sig` 达到 ≥6（核心判据），然后自动判定
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TGT=${1:-6}; LIM=${2:-7200}; T=0
echo "  等 t5B12 的 n_var_sig ≥ $TGT（最多 ${LIM} s；A 臂对照值 = 3）"
while [ "$T" -lt "$LIM" ]; do
  V=$($PY - <<'PYEOF' 2>/dev/null
import csv, os
P = '_exp/_bk_t5/dry_t5B12/series.csv'
if not os.path.exists(P):
    print(-1); raise SystemExit
rows = [r for r in csv.DictReader(open(P, newline='')) if (r.get('n_var_sig') or '').strip().isdigit()]
print(int(rows[-1]['n_var_sig']) if rows else -1)
PYEOF
)
  [ -n "$V" ] && [ "$V" -ge "$TGT" ] 2>/dev/null && { echo "  ★ n_var_sig = $V（达到 $TGT）"; break; }
  P=$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5B12')
  [ "$P" -eq 0 ] && { echo "  ⚠ t5B12 进程消失（n_var_sig 停在 $V）"; break; }
  sleep 90; T=$((T + 90))
done
echo "NOW = $(date '+%F %T')  等了 ${T} s"
echo
echo '════ ★ 两臂对照：--B 3（对照） vs --B 12（修复）════'
$PY - <<'PYEOF'
import csv, os
def last(tag, keys):
    P = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(P):
        return None
    rows = list(csv.DictReader(open(P, newline='')))
    br = [r for r in rows if (r.get('nblk_sig') or '').strip()]
    return (br[-1] if br else None), (rows[-1] if rows else None)
print('  %-14s %-8s %-9s %-10s %-9s %-8s %s'
      % ('臂', '末步', 'n_var_sig', 'nblk_sig', 'nslab_n', 'nf2', 'blk_laths'))
for tag, lab in (('t5N276F', '--B 3 (对照)'), ('t5B12', '--B 12 (修复)')):
    r = last(tag, None)
    if not r or not r[0]:
        print('  %-14s （无块表行）' % lab); continue
    b, s = r
    print('  %-14s %-8s **%-9s** %-10s %-9s %-8s %s'
          % (lab, (s or {}).get('step', '?'), b.get('n_var_sig'), b.get('nblk_sig'),
             b.get('nslab_n'), b.get('nf2'), (b.get('blk_laths') or '')[:28]))
print()
print('  ── 判据（**预先写死**）──')
print('  * A 臂（--B 3）实测 `n_var_sig` = **3**（自协调需 12）;')
print('  * **若 B 臂 `n_var_sig` 显著上升（≥6，理想 →12）⇒ 设计级根因确认** ✓;')
print('  * 若仍 ≈3 ⇒ 块目标未转化为变体数 ⇒ 需查 `var-rule` 在 fresh 里的实际选择。')
PYEOF
echo
echo '════ `Δed` 带符号（自协调是否生效；A 臂 = −2.955e8，<0 占 100%）════'
grep -E 'Δed 带符号' _w2_t5_short_t5B12.log 2>/dev/null | tail -3 | cut -c1-190 | sed 's/^/  /'
echo '  （若为空 ⇒ 诊断还没到输出步）'
