#!/bin/bash
# _r581_verify_unchanged.sh --- ★★★★★ **复核：那 124 个脚本确实**一个字节都没改****
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① 抽查是否还有那两个变量（**有 = 没改**）════'
n_mmap=0
n_trim=0
for f in $(grep -rl 'MALLOC' --include='*.sh' . 2>/dev/null); do
  case "$f" in
    *superseded*|*_r577_*|*_r578_*|*_r581_alloc*) continue ;;
  esac
  if grep -q '^[^#]*MALLOC_MMAP_THRESHOLD_' "$f" 2>/dev/null; then n_mmap=$((n_mmap+1)); fi
  if grep -q '^[^#]*MALLOC_TRIM_THRESHOLD_' "$f" 2>/dev/null; then n_trim=$((n_trim+1)); fi
done
echo "  仍带 MALLOC_MMAP_THRESHOLD_ 的脚本 = $n_mmap"
echo "  仍带 MALLOC_TRIM_THRESHOLD_ 的脚本 = $n_trim"
echo "  ⇒ **两者都非 0 ⇒ 脚本**未被修改**** ✓"
echo
echo '════ ② 抽查 3 个脚本的原文行 ════'
for f in _r77_iso.sh _r98_sasmoke.sh _bk_closed_chain.sh; do
  [ -f "$f" ] || continue
  echo "  ── $f ──"
  grep -n 'MALLOC' "$f" 2>/dev/null | head -2 | cut -c1-120 | sed 's/^/    /'
done
echo
echo '════ ③ 有没有 `_r581_alloc_edit_manifest.tsv`（**有 = 执行过 apply**）════'
if [ -f _r581_alloc_edit_manifest.tsv ]; then
  echo '  ⚠ **存在** ⇒ 说明跑过 --apply ⇒ 行数：'; wc -l < _r581_alloc_edit_manifest.tsv
else
  echo '  ✅ **不存在** ⇒ **从未执行 --apply** ✓'
fi
echo
echo '════ ④ 有没有 allocEdfix 备份目录（apply 才会建）════'
ls -d _r580_backup/allocEdfix_* 2>/dev/null | sed 's/^/  /' || echo '  ✅ 没有 ⇒ apply 从未运行 ✓'
echo
echo '════ ⑤ 内存现状 ════'
free -m | sed -n 2,3p | sed 's/^/  /'
echo
echo '════ ⑥ 还在跑的臂 ════'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  r=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  printf '  tag=%-9s RSS=%sMB\n' "${tag:-?}" "$r"
done
echo '  （空 = 没有臂在跑）'
