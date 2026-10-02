#!/bin/bash
# _r581_bcheck.sh --- ★★★★★ **排除"`B` 根本没生效"**（否则"饱和"是假象，我的量具就错了）
#   P24 的同类：每条判据配**能失败**的负对照；这里先证 `B` **确实传进去了**。
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
for T in E F G D; do
  f="_w2_r581_mn64_${T}.log"
  [ -f "$f" ] || f="_w2_r581_mn64${T}.log"
  echo "################ 臂 $T ################"
  if [ ! -f "$f" ]; then echo "  （无日志）"; continue; fi
  echo "  ── 命令行里的 --nuc-block-target ──"
  grep -oE '\-\-nuc-block-target [0-9]+' "$f" 2>/dev/null | sort -u | sed 's/^/    /'
  echo "  ── 日志里所有含 tgt / target / 目标 的行（前 6 条）──"
  grep -inE 'tgt|target|目标' "$f" 2>/dev/null | head -6 | cut -c1-96 | sed 's/^/    /'
  echo "  ── 形核事件统计（前 3 条 athermal 行）──"
  grep -n 'athermal' "$f" 2>/dev/null | head -3 | cut -c1-96 | sed 's/^/    /'
  echo
done
echo '################ 参数是怎么进引擎的 ################'
grep -n "nuc_block_target" _bk_exp.py 2>/dev/null | head -8 | cut -c1-100 | sed 's/^/  /'
echo
echo '################ 引擎侧：谁消费这个量 ################'
grep -n "block_target" windowB_surface.py _bk_exp.py 2>/dev/null | head -8 | cut -c1-100 | sed 's/^/  /'
