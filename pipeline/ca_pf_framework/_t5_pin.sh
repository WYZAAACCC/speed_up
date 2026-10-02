#!/bin/bash
# _t5_pin.sh --- 查 `P0` **钉基准**代码的真实位置（**不截断行** —— §16.3 的教训）
cd "$(dirname "$0")" || exit 1
echo '════ ① 钉基准的判据在哪里（不截断）════'
grep -n 'P0 is None' _bk_exp.py 2>/dev/null | sed 's/^/  /'
echo
echo '════ ② `pm` 的定义与有限性判据所在处（不截断）════'
grep -nE 'pm *=|isfinite\(pm\)' _bk_exp.py 2>/dev/null | sed 's/^/  /'
echo
echo '════ ③ 两处写入点各自的行文（不截断）════'
sed -n '2755,2765p' _bk_exp.py | sed 's/^/  [2755+] /'
echo '  ---'
sed -n '2976,2986p' _bk_exp.py | sed 's/^/  [2976+] /'
