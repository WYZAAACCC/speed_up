#!/bin/bash
# _t5_therm.sh --- 关键岔路：本仓库有没有**可用的真实热史 T(t)**（决定 S14 的处置）
cd /mnt/f/speed_up || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① Window A / 熔池 的产物目录 ════'
for d in pipeline/windowA pipeline/window_a pipeline/meltpool pipeline/wa \
         pipeline/ca_pf_framework/windowA _exp/wa _exp/windowA _exp/meltpool; do
  [ -d "$d" ] && { echo "  ✅ $d"; ls -1 "$d" 2>/dev/null | head -8 | sed 's/^/      /'; }
done
echo '  ── 全库找"热史/温度历史"类文件 ──'
find . -maxdepth 4 \( -iname '*therm*' -o -iname '*thist*' -o -iname '*cool*' \
     -o -iname '*t_history*' -o -iname '*Tt*' \) -type f 2>/dev/null \
  | grep -v '\.git/' | head -20 | sed 's/^/    /'
echo
echo '════ ② 代码里的热史入口（T_of_t 的构造点）════'
cd pipeline/ca_pf_framework || exit 1
grep -rn 'def linear_cool\|def drive_of_T\|def T_of_t' windowB_km.py 2>/dev/null | cut -c1-118 | sed 's/^/  /'
echo '  ── linear_cool 的实体（前 24 行）──'
sed -n "$(grep -n 'def linear_cool' windowB_km.py | head -1 | cut -d: -f1),+24p" windowB_km.py 2>/dev/null \
  | cut -c1-118 | sed 's/^/    /'
echo
echo '════ ③ 有没有别的热史实现（非线性/分段）════'
grep -rn 'def .*cool\|def .*therm\|def .*hist' windowB_km.py 2>/dev/null | cut -c1-118 | sed 's/^/  /'
echo
echo '════ ④ 归档里已有的"冷却曲线"数据（series.csv 的 T 列）════'
echo '  ── abA 的 T 轨迹（前 5 / 后 5 行）──'
head -1 _exp/_bk_mb/dry_abA/series.csv | tr ',' '\n' | grep -n '^T$\|^t_s$\|wall_s' | sed 's/^/    /'
