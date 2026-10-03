#!/bin/bash
# _t5_fcheck.sh --- ★ 验硬要求：「全部仿真数据存 F 盘」（无数据只留在 WSL）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 各臂的数据目录与体积（应在 /mnt/f 下）════'
for d in _exp/_bk_t5/dry_* _exp/_bk_mb/dry_*; do
  [ -d "$d" ] || continue
  printf '  %-34s %8s   ckpt=%s snap=%s\n' "$d" \
    "$(du -sh "$d" 2>/dev/null | cut -f1)" \
    "$(ls -1 "$d"/ckpt/*.npz 2>/dev/null | wc -l)" \
    "$(ls -1 "$d"/snap_*.npz 2>/dev/null | wc -l)"
done
echo
echo '════ ② 合计 ════'
du -sh _exp 2>/dev/null | sed 's/^/  总: /'
echo
echo '════ ③ ★ 关键：WSL 侧有没有"只在这里"的仿真数据？════'
echo '  （若有，则违反"存 F 盘"这条硬要求）'
for p in /root/work /root/_exp /root/ca_pf_framework /tmp/_exp; do
  if [ -e "$p" ]; then
    echo "  ⚠ 存在 $p ⇒ 查它是否含产物："
    ls -1 "$p" 2>/dev/null | head -5 | sed 's/^/      /'
  else
    echo "  ✅ $p 不存在"
  fi
done
echo
echo '  ── 全盘搜 WSL 侧的 series.csv（产物指纹）──'
find /root /home /tmp -maxdepth 5 -name 'series.csv' 2>/dev/null | head -8 | sed 's/^/    /'
echo '  （上面若为空 ⇒ **没有产物只留在 WSL** ✓）'
