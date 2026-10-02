#!/bin/bash
# _r581_crit11.sh --- ★★★★★ 复核 **goal 判据⑪**：简化审计逐条有结论 + "驱动力随温度变"有实测证据
#
# goal 判据⑪ 逐字：
# 「简化审计**逐条有结论**（保留/取消 + 代价收益记账）；"**驱动力随温度变**"有**实测证据**」
cd "$(dirname "$0")" || exit 1
A=R581_SIMPLIFICATION_AUDIT.md
echo "NOW = $(date '+%F %T')"
echo
echo '════════ ① 简化审计文档 ════════'
if [ -f "$A" ]; then
  wc -l < "$A" | sed 's/^/  行数=/'
  echo '  ── 判定词出现次数 ──'
  for w in 保留 取消 已修 待修 未做 部分 否定 判死; do
    printf '    %-6s %s\n' "$w" "$(grep -c "$w" "$A")"
  done
  echo '  ── S1–S13 条目是否都在 ──'
  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13; do
    c=$(grep -c "S$i\b" "$A")
    printf '    S%-3s 命中 %s 行\n' "$i" "$c"
  done
else
  echo "  ⚠ 没有 $A"
fi
echo
echo '════════ ② "驱动力随温度变"的**实测证据** ════════'
echo '  （要日志里**打印出来的** df 随时间变化，不是只看代码）'
for f in _w2_r581_blk_BK6.log _w2_r581_blk_BG2.log _w2_r581_mn64_F.log; do
  [ -f "$f" ] || continue
  echo "  ── $f ──"
  grep -o 'df[^，,;]*' "$f" 2>/dev/null | head -4 | sed 's/^/    /'
done
echo
echo '  ── `series.csv` 里的 df 列（更可靠：逐步数列）──'
PY=/root/miniconda3/envs/ml/bin/python
$PY - <<'PYEOF'
import csv, os
p = '_exp/_bk_blk/dry_BK6/series.csv'
if not os.path.exists(p):
    print('    （没有 %s）' % p)
else:
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    hdr = list(rows[0].keys())
    cand = [c for c in hdr if c.lower().startswith('df') or 'drive' in c.lower()]
    print('    df/drive 类列：%s' % (cand if cand else '（无）'))
    for c in cand[:4]:
        vals = []
        for r in rows[:6]:
            v = (r.get(c, '') or '').strip()
            vals.append(v)
        print('      %-16s 前 6 步：%s' % (c, ', '.join(vals)))
PYEOF
echo
echo '★ 判读：**df 列随步数变化** ⇒ 判据⑪ 的后半成立；**S1–S13 都有判定词** ⇒ 前半成立'
