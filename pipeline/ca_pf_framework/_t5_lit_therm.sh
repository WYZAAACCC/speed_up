#!/bin/bash
# _t5_lit_therm.sh --- 文献缓存里有没有可依据的 LPBF 热史（决定 S14 能否"按物理正确实现"）
cd /mnt/f/speed_up || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① 文献缓存的规模 ════'
printf '  lit/cache: %s 个文件\n' "$(ls -1 lit/cache 2>/dev/null | wc -l)"
printf '  lit/cache 里 .txt: %s 个\n' "$(ls -1 lit/cache/*.txt 2>/dev/null | wc -l)"
echo
echo '════ ② ★ 搜"冷却速率 / 热史 / 温度历史"相关段落 ════'
for kw in 'cooling rate' 'cooling-rate' 'thermal history' 'thermal cycle' \
          'temperature history' 'K/s' 'peak temperature' 'reheat' 'remelting'; do
  n=$(grep -ril "$kw" lit/cache/*.txt .litsearch/txt/*.txt 2>/dev/null | wc -l)
  printf '  %-20s 命中文件 %s 个\n' "$kw" "$n"
done
echo
echo '════ ③ 命中最多的文件 + 具体句子（前 14 条）════'
grep -rin 'cooling rate\|thermal cycle\|thermal history' lit/cache/*.txt .litsearch/txt/*.txt 2>/dev/null \
  | grep -oE '^[^:]+:[0-9]+:.{0,150}' | head -14 | sed 's/^/  /'
echo
echo '════ ④ 有没有专门的"热史"文档 ════'
ls -la docs/LIT_SEARCH_BRIEF_Ti64_THERMO.md 2>/dev/null | sed 's/^/  /'
grep -n '冷却\|冷速\|热史\|K/s' docs/LIT_SEARCH_BRIEF_Ti64_THERMO.md 2>/dev/null | head -14 | cut -c1-118 | sed 's/^/    /'
