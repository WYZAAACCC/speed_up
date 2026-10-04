#!/bin/bash
# _t5_vrscope.sh --- ★★★★★ 核验 `var_rule` 的生效通道（是否与 `supercrit` 同一个"只覆盖 fresh"缺口）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `var_rule` / `var-rule` 的全部出现处 ════'
grep -nE "var_rule|var-rule" windowB_surface.py _bk_exp.py 2>/dev/null | head -18 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② 它在哪条通道被**读取**（看缩进/所在分支）════'
for LN in $(grep -n "c.get('var_rule'" windowB_surface.py | cut -d: -f1); do
  echo "  ── 第 $LN 行所在位置（向上找最近的 def 与通道关键字）──"
  sed -n "1,${LN}p" windowB_surface.py | grep -nE '^    def |模式 \*\*|attach|stack|fresh' | tail -5 | cut -c1-130 | sed 's/^/     /'
done
echo
echo '════ ③ ★ 与 `supercrit` 的对比（两者是否同一缺口）════'
echo "  supercrit 调用点：$(grep -n "c.get('supercrit'" windowB_surface.py | cut -d: -f1 | tr '\n' ' ')"
echo "  var_rule  读取点：$(grep -n "c.get('var_rule'" windowB_surface.py | cut -d: -f1 | tr '\n' ' ')"
echo "  ⇒ 若两组行号都在**同一段**（fresh 分支，约 2050–2200 行）⇒ **同一个缺口**"
echo
echo '════ ④ 实测：`t5N276F` 的变体数与块结构（自协调的证据）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import csv, os
P = '_exp/_bk_t5/dry_t5N276F/series.csv'
if os.path.exists(P):
    rows = [r for r in csv.DictReader(open(P, newline='')) if (r.get('nblk_sig') or '').strip()]
    for r in rows[-3:]:
        print('  step %-6s nslab_n=%-4s n_var_sig=**%s**  nblk_sig=%-4s blk_laths=%s'
              % (r['step'], r.get('nslab_n'), r.get('n_var_sig'), r.get('nblk_sig'),
                 (r.get('blk_laths') or '')[:30]))
    print()
    ks = [int(r['n_var_sig']) for r in rows if (r.get('n_var_sig') or '').strip().isdigit()]
    if ks:
        print('  `n_var_sig` 末值 = **%d**（自协调需要 **12** 个变体齐全）' % ks[-1])
        print('  ⇒ %s' % ('**远未自协调** ⇒ 罚能无法抵消 ⇒ 板条溶解 ✓'
                          if ks[-1] < 8 else '变体数较全'))
else:
    print('  （无 series.csv）')
PYEOF
