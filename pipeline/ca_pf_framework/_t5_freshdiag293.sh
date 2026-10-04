#!/bin/bash
# s293 判据 1 FAIL 的分诊：fresh 通道到底发生了什么？
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for T in t5ETAo t5BKMo t5FIX; do
  L=_w2_t5_short_$T.log
  [ -f "$L" ] || continue
  echo "════ $T ════"
  echo -n "  形核事件数（块内第）= "; grep -ac '块内第' $L
  echo -n "  fresh 被拒退回 stack = "; grep -ac 'fresh` 被拒' $L
  echo -n "  被引擎拒（完全失败） = "; grep -ac '被引擎拒' $L
  echo "  模式分布："
  grep -a '模式 \*\*' $L | grep -oE '模式 \*\*[a-z]+\*\*' | sort | uniq -c | sed 's/^/     /'
  echo "  ★ fresh 事件明细（若有）："
  grep -a '模式 \*\*fresh\*\*' $L | tail -3 | grep -oE 'step [0-9]+：T=[0-9.]+ K.*累计 [0-9]+/[0-9]+' | cut -c1-90 | sed 's/^/     /'
  echo "  fresh 被拒退回 stack 明细："
  grep -a 'fresh` 被拒' $L | tail -3 | cut -c1-110 | sed 's/^/     /'
done
echo
echo "=== 构造横幅里的三行（口径自证）==="
for T in t5ETAo; do
  grep -aE '平行建块|N8|块数口径' _w2_t5_short_$T.log | head -4 | cut -c1-190 | sed 's/^/  /'
done
