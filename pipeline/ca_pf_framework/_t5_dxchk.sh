#!/bin/bash
# _t5_dxchk.sh --- 读 t5DX32（dx=31.25）的 |Δed|（决定性）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -- '--tag t5DX32' | grep -v grep | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  ps -o pid,etime,time,pcpu --no-headers -p "$P" | sed 's/^/  进程 /'
else
  echo '  ⚠ 进程不在'
fi
printf '  末步 = %s ｜ 诊断块 = %s ｜ 快照 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5DX32/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(grep -c '三项量级' _w2_t5_short_t5DX32.log 2>/dev/null)" \
  "$(ls -1 _exp/_bk_t5/dry_t5DX32/snap_*.npz 2>/dev/null | wc -l)"
echo
echo '════ ★ dx=31.25（10 胞厚）的 |Δed| ════'
grep -E 'F1 含母相|Δed 带符号' _w2_t5_short_t5DX32.log 2>/dev/null | tail -4 | cut -c1-205 | sed 's/^/  /'
echo
echo '════ 对照 dx=62.5（5 胞厚）的 |Δed|（t5B4D）════'
grep -E 'F1 含母相|Δed 带符号' _w2_t5_short_t5B4D.log 2>/dev/null | tail -4 | cut -c1-205 | sed 's/^/  /'
echo
echo '════ 判据 ════'
echo '  · dx 减半（5→10 胞厚）后 |Δed| **显著下降** ⇒ **欠解析**（修法=加密网格）'
echo '  · 基本不变 ⇒ 罚能是**物理量** ⇒ 查 ε⁰/C/Ms 标定'
free -m | sed -n 2p | sed 's/^/  /'
