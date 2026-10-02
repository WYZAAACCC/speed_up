#!/bin/bash
# _t5_vrchk.sh --- 查 `--var-rule` 在启动器与引擎 CLI 里的现状
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 启动器 `_t5_short.py` 里有没有 var-rule ════'
grep -n 'var.rule' _t5_short.py | sed 's/^/  /'
echo '  （空 = 没透传 ⇒ 引擎会用默认 ed）'
echo
echo '════ ② 引擎 CLI 的定义与默认 ════'
grep -n 'var-rule' _bk_exp.py | sed 's/^/  /'
echo
echo '════ ③ 引擎里最终传给 nuc_cfg 的那一处 ════'
grep -n 'var_rule=' _bk_exp.py | sed 's/^/  /'
