#!/bin/bash
# _t5_b12nchk.sh --- 读 t5B12N 的关键判据（n_var_sig 是否 3→12）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=t5B12N
echo "NOW = $(date '+%F %T')"
echo '── 进程 / 进度 / 内存 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
printf '  末步 = %s ｜ 快照 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(ls -1 _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)"
free -m | sed -n 2p | sed 's/^/  /'
echo
echo '════ ★ 判据①：`n_var_sig`（A 臂 --B 3 实测 = 3；目标 →12）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import csv, os
for tag, lab in (('t5B12N', '--N 100 --B 12 (修复)'), ('t5N276F', '--N 80 --B 3 (对照)')):
    P = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(P):
        print('  %-24s （无数据）' % lab); continue
    rows = [r for r in csv.DictReader(open(P, newline='')) if (r.get('nblk_sig') or '').strip()]
    print('  ── %s（块表 %d 行）──' % (lab, len(rows)))
    for r in rows[-4:]:
        print('     step %-6s nslab_n=%-4s **n_var_sig=%s** nblk_sig=%-4s nf2=%-6s blk_laths=%s'
              % (r['step'], r.get('nslab_n'), r.get('n_var_sig'), r.get('nblk_sig'),
                 r.get('nf2'), (r.get('blk_laths') or '')[:26]))
    ks = [int(r['n_var_sig']) for r in rows if (r.get('n_var_sig') or '').strip().isdigit()]
    if ks:
        print('     ⇒ **n_var_sig 末值 = %d**%s' % (ks[-1], '  ← **达到 12！自协调成立** ✓' if ks[-1] >= 12 else
              ('  ← 上升中' if ks[-1] > 3 else '')))
PYEOF
echo
echo '════ 形核事件模式分布（fresh 是否变多）════'
for m in fresh attach stack; do
  printf '  %-7s = %s\n' "$m" "$(grep -cE "模式 \*\*$m\*\*" _w2_t5_short_$TAG.log 2>/dev/null)"
done
echo '════ 被拒次数（应为 0）════'
grep -c '被引擎拒' _w2_t5_short_$TAG.log 2>/dev/null | sed 's/^/  /'
echo
echo '════ 判据②：`Δed` 带符号（A 臂 = −2.955e8，<0 占 100%）════'
grep -E 'Δed 带符号' _w2_t5_short_$TAG.log 2>/dev/null | tail -3 | cut -c1-195 | sed 's/^/  /'
echo '  （为空 ⇒ 诊断还没到输出步）'
echo
echo '════ 判据③：Vt 轨迹（是否还在流失）════'
grep -E '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -5 | cut -c1-120 | sed 's/^/  /'
