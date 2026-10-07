#!/bin/bash
# _r245_q17.sh —— ★ 查 **Q-17**：`p45L` / `p45P` 两臂的产物**是不是同一个文件**？
#
# 判据：
#   Q17-1 两个目录都存在、且**不是同一个 inode**
#   Q17-2 两个 `series.csv` 的 **inode 不同**、大小/mtime 独立演进
#   Q17-3 `meta.json` 里的 `tag` / `omega_mode` 各自正确
#   Q17-4 若全部相同 ⇒ 两臂写了同一份 ⇒ `_r225` 的对照**作废**
cd "$(dirname "$0")" || exit 1
echo "=== ① 目录 ==="
for d in p45L p45P; do
  if [ -d "_exp/_bk_mb/dry_$d" ]; then
    printf '  %-8s inode=%s  文件数=%s\n' "$d" \
      "$(stat -c %i "_exp/_bk_mb/dry_$d")" \
      "$(ls -1 "_exp/_bk_mb/dry_$d" | wc -l)"
  else
    printf '  %-8s ❌ 目录不存在\n' "$d"
  fi
done
echo
echo "=== ② series.csv 的 inode / 大小 / mtime ==="
stat -c '  %n  inode=%i  size=%s  mtime=%y' \
  _exp/_bk_mb/dry_p45L/series.csv _exp/_bk_mb/dry_p45P/series.csv 2>/dev/null
echo
echo "=== ③ 前 3 行逐字节比较 ==="
if cmp -s <(head -3 _exp/_bk_mb/dry_p45L/series.csv) \
          <(head -3 _exp/_bk_mb/dry_p45P/series.csv); then
  echo "  ⚠ 前 3 行**逐字节相同**"
else
  echo "  ✅ 前 3 行不同"
fi
echo
echo "=== ③b 第 5 行（step 80）逐字节比较 ==="
if cmp -s <(sed -n '5p' _exp/_bk_mb/dry_p45L/series.csv) \
          <(sed -n '5p' _exp/_bk_mb/dry_p45P/series.csv); then
  echo "  ⚠ step 80 行**逐字节相同**"
else
  echo "  ✅ step 80 行不同"
fi
echo
echo "=== ④ meta 的关键字段 ==="
for d in p45L p45P; do
  f="_exp/_bk_mb/dry_$d/meta.json"
  [ -f "$f" ] || { echo "  $d: 无 meta"; continue; }
  /root/miniconda3/envs/ml/bin/python -c "
import json,sys
m=json.load(open(sys.argv[1]))
print('  %-8s tag=%-8s omega_mode=%-9s omega_max_deg=%-8s nthreads=%s' % (
 '$d', m.get('tag'), m.get('omega_mode'), m.get('omega_max_deg'), m.get('nthreads')))" "$f"
done
echo
echo "=== ⑤ 逐行 diff 计数（整份 series.csv）==="
if diff -q _exp/_bk_mb/dry_p45L/series.csv _exp/_bk_mb/dry_p45P/series.csv \
     >/dev/null 2>&1; then
  echo "  ❌ **两份 series.csv 完全相同 ⇒ Q-17 命中 (a)/(c)：两臂写了同一份数据**"
else
  echo "  ✅ 两份不同；不同的行数 = $(diff _exp/_bk_mb/dry_p45L/series.csv \
    _exp/_bk_mb/dry_p45P/series.csv | grep -c '^[<>]' || true)"
fi
