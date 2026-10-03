#!/bin/bash
# _t5_chkv2.sh --- 查 V2 臂是否在跑
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
echo
echo '── V2 横幅关键行 ──'
grep -E '导出板条数|总根数|必须至少|不自洽|N8 自动推导|var-rule' \
  _w2_t5_short_t5V2.log 2>/dev/null | head -6 | cut -c1-132 | sed 's/^/  /'
echo '  （若出现"不自洽"⇒ 仍未通过；若无 ⇒ 已进入运行）'
echo
echo '── V2 日志体积与末次修改 ──'
for f in _w2_t5_short_t5V2.log _w2_t5_v2b_A.log; do
  printf '  %-26s %s 字节  %s\n' "$f" "$(stat -c%s "$f" 2>/dev/null || echo 0)" \
    "$(stat -c%y "$f" 2>/dev/null | cut -c1-19)"
done
echo
free -m | sed -n 2p | sed 's/^/  /'
