#!/bin/bash
# _t5_add.sh --- 显式暂存 `_t5_*`（先按体积过滤，绝不 `git add -A`）
cd /mnt/f/speed_up || exit 1
cd pipeline/ca_pf_framework || exit 1
echo '── 候选（体积 ≥ 512 KB 的**一律跳过**）──'
BIG=0
for f in _t5_*.sh _t5_*.py; do
  [ -f "$f" ] || continue
  SZ=$(stat -c%s "$f")
  if [ "$SZ" -gt 524288 ]; then
    printf '  ⏭ 跳过 %-34s %.2f MB（>512 KB）\n' "$f" "$(echo "$SZ/1048576" | bc -l)"
    BIG=$((BIG+1)); continue
  fi
  printf '  ✅ %-34s %6d B\n' "$f" "$SZ"
done
echo "  （跳过大文件 $BIG 个）"
echo
echo '── 安全检查：候选里有没有二进制痕迹 ──'
if grep -lIP '\x00' _t5_*.sh _t5_*.py 2>/dev/null; then
  echo '  ❌ 上面这些含 NUL 字节 ⇒ **中止**'
  exit 1
fi
echo '  ✅ 无 NUL 字节'
echo
git add -v _t5_*.sh _t5_*.py 2>&1 | tail -6
echo
echo '── 暂存区汇总 ──'
git diff --cached --stat | tail -4
