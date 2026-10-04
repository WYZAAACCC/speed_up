#!/bin/bash
# _t5_freshsw.sh --- 查 `_t5_short.py` 是否已有 `--nuc-fresh-every` 透传
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `_t5_short.py` 里 nuc_fresh_every 的出现处 ════'
grep -n 'nuc_fresh_every\|nuc-fresh-every' _t5_short.py 2>/dev/null | cut -c1-175 | sed 's/^/  /'
echo
echo '════ ② 对应的透传代码段（上下文）════'
L=$(grep -n 'nuc_fresh_every' _t5_short.py | head -1 | cut -d: -f1)
if [ -n "$L" ]; then
  S=$((L-6)); E=$((L+8))
  sed -n "${S},${E}p" _t5_short.py | nl -ba -v"$S" | cut -c1-165 | sed 's/^/  /'
else
  echo '  ⚠ 未找到 ⇒ 需要加透传'
fi
echo
echo '════ ③ 引擎侧参数的默认值与语义 ════'
grep -nE "add_argument\('--nuc-fresh-every" _bk_exp.py | cut -c1-175 | sed 's/^/  /'
grep -nE 'nuc_fresh_every' _bk_exp.py | head -8 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ④ 实测：`t5N276F` 日志里 `fresh` 相关计数 ════'
grep -oE 'fresh=[0-9]+ stack=[0-9]+' _w2_t5_short_t5N276F.log 2>/dev/null | tail -3 | sed 's/^/  /'
grep -cE '模式 \*\*fresh\*\*' _w2_t5_short_t5N276F.log 2>/dev/null | sed 's/^/  fresh 事件数 = /'
grep -cE '模式 \*\*attach\*\*' _w2_t5_short_t5N276F.log 2>/dev/null | sed 's/^/  attach 事件数 = /'
grep -cE '模式 \*\*stack\*\*' _w2_t5_short_t5N276F.log 2>/dev/null | sed 's/^/  stack 事件数 = /'
