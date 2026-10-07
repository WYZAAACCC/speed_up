#!/bin/bash
# _t5_ckchk276.sh --- 断点续跑就绪性核对（用户明确要求的功能）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 检查点文件（--ckpt-every 100 --ckpt-keep 2）════'
ls -1 _exp/_bk_t5/dry_t5N276/ckpt/*.npz 2>/dev/null | while read -r f; do
  printf '  %-46s %8s 字节  %s\n' "$(basename "$f")" "$(stat -c%s "$f")" "$(stat -c%y "$f" | cut -d. -f1)"
done
echo
printf '  ckpt 个数 = %s\n' "$(ls -1 _exp/_bk_t5/dry_t5N276/ckpt/*.npz 2>/dev/null | wc -l)"
echo
echo '════ 进度 ════'
printf '  末步 = %s   快照 = %s   引擎进程 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(ls -1 _exp/_bk_t5/dry_t5N276/snap_*.npz 2>/dev/null | wc -l)" \
  "$(ps -eo args --no-headers 2>/dev/null | grep -c -- '--tag t5N276')"
echo
echo '════ 恢复命令（备查；**不要现在跑**）════'
echo '  python _t5_short.py --tag t5N276 --N 80 --nvar 12 --m 23 --B 3 --steps 6000 \'
echo '      --cores 0-7 --mem-limit-gb 8.0 --every 20 --snap-every 40 --pair-every 100 \'
echo '      --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \'
echo '      --resume _exp/_bk_t5/dry_t5N276/ckpt'
echo '  ⚠ 启动器必须 wait / 用 setsid（否则 SIGHUP 会杀它 —— 本项目记过两次）'
