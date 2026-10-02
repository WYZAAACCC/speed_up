#!/bin/bash
# _t5_order.sh --- 确认"钉基准(:2794)"与"写检查点"的**真实先后**
cd "$(dirname "$0")" || exit 1
echo '════ ① 检查点调用点在主循环里的行号 ════'
grep -nE '_ckpt_gather\(|ckpt_gather\(' _bk_exp.py 2>/dev/null | sed 's/^/  /'
echo
echo '════ ② `_ckpt_now` / 检查点门控的定义与使用 ════'
grep -nE '_ckpt_now|_ckpt_every|ckpt_now' _bk_exp.py 2>/dev/null | head -12 | sed 's/^/  /'
echo
echo '════ ③ `P0` 是否**只**用于诊断（决定能否安全移动）════'
grep -nE '(^|[^_A-Za-z])P0([^_A-Za-z0-9]|$)' _bk_exp.py 2>/dev/null | wc -l | sed 's/^/  出现次数: /'
echo '  ── 逐处（不截断）──'
grep -nE '(^|[^_A-Za-z])P0([^_A-Za-z0-9]|$)' _bk_exp.py 2>/dev/null | sed 's/^/  /'
