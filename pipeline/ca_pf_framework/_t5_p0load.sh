#!/bin/bash
# _t5_p0load.sh --- 查 `f3_pos_p0_m` 的**写入**与**读回**两侧
cd "$(dirname "$0")" || exit 1
echo '════ ① 所有出现 `f3_pos_p0_m` 的地方 ════'
grep -n 'f3_pos_p0_m' _bk_exp.py 2>/dev/null | cut -c1-136 | sed 's/^/  /'
echo
echo '════ ② `P0` 这个变量名在哪被赋值/读取 ════'
grep -nE '(^|[^_a-zA-Z])P0[^_a-zA-Z0-9]' _bk_exp.py 2>/dev/null | head -14 | cut -c1-132 | sed 's/^/  /'
echo
echo '════ ③ 检查点**装载**函数里的键循环（看有没有漏 P0）════'
LN=$(grep -n 'def _ckpt_load\|def _load_ckpt\|ckpt_ver' _bk_exp.py 2>/dev/null | head -1 | cut -d: -f1)
echo "  （装载相关起点 = $LN）"
if [ -n "$LN" ]; then
  sed -n "$((LN)),$((LN+44))p" _bk_exp.py | grep -nE "z\['|\.get\('|for k in|keys\(\)|P0|p0" | head -22 | cut -c1-128 | sed 's/^/    /'
fi
