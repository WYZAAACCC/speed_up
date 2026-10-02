#!/bin/bash
# _t5_blk_diag.sh --- 判据④/⑥ 的量具为什么在 abA 里空白：找日志里的那行警告
cd "$(dirname "$0")" || exit 1
echo '════ ① abA 的 stdout 日志在哪 ════'
ls -la _w2_*abA* *abA*.log 2>/dev/null | sed 's/^/  /'
for f in $(grep -ln '块表计算失败' _w2_*.log 2>/dev/null | head -5); do
  printf '  ★ **含"块表计算失败"**：%s（%s 次）\n' "$f" "$(grep -c '块表计算失败' "$f")"
done
echo
echo '════ ② 全库扫：哪些日志出现过这条警告 ════'
grep -l '块表计算失败' _w2_*.log 2>/dev/null | head -12 | sed 's/^/  /'
echo '  ── 警告的具体内容（前 6 条，去重）──'
grep -h '块表计算失败' _w2_*.log 2>/dev/null | sed 's/.*块表计算失败/块表计算失败/' | sort -u | head -6 | cut -c1-140 | sed 's/^/    /'
echo
echo '════ ③ 反查：哪些算例的 series.csv 里 blk 列**非空**（说明量具本来是好的）════'
PY=/root/miniconda3/envs/ml/bin/python
$PY - <<'PYEOF'
import csv, glob, os
good, bad, none = [], [], 0
for p in sorted(glob.glob('_exp/*/dry_*/series.csv'))[:400]:
    try:
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    except Exception:
        continue
    if not rows or 'nblk_sig' not in rows[0]:
        none += 1; continue
    vals = set((r.get('nblk_sig') or '').strip() for r in rows)
    nz = [v for v in vals if v not in ('', '0')]
    tag = os.path.basename(os.path.dirname(p))
    if nz:
        good.append((tag, sorted(nz)[:4], len(rows)))
    else:
        bad.append(tag)
print('  有 nblk_sig 列的算例：**非空 %d 个** / 全空 %d 个 / 无此列 %d 个'
      % (len(good), len(bad), none))
print()
print('  ── ★ 非空的（**说明量具不是天生坏的**）前 14 个 ──')
for t, v, n in good[:14]:
    print('    %-22s nblk_sig 取值 %-22s (%d 行)' % (t, v, n))
if not good:
    print('    ⚠ **一个都没有** ⇒ 量具从来没出过数 ⇒ 是系统性缺陷，不是配置问题')
PYEOF
