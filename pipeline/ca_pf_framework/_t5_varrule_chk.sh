#!/bin/bash
# _t5_varrule_chk.sh --- ★★★★★ 验证"`--var-rule ed` ⇒ 永远同一个变体"（决定④⑤能否达成）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `--var-rule` 的定义与取值 ════'
grep -n "add_argument('--var-rule'" _bk_exp.py | cut -c1-175 | sed 's/^/  /'
echo
echo '════ ② `var_rule` 在引擎里的**使用处**（谁读它）════'
grep -n "var_rule" _bk_exp.py | cut -c1-155 | sed 's/^/  /'
echo
echo '════ ③ ★ 它被传给谁：`fresh` 通道还是所有通道？════'
grep -n "var_rule=\|var_rule'" _bk_exp.py | cut -c1-155 | sed 's/^/  /'
echo
echo '════ ④ `windowB_km.py` 里 `var_rule` 怎么选变体（`ed` vs `random`）════'
grep -n "var_rule\|def pick_var\|argmax" windowB_km.py 2>/dev/null | head -12 | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ⑤ 本次运行的**实际取值**（从进程命令行）════'
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5N276' | awk '{print $1}'); do
  tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-var-rule [a-z]+|\-\-nuc-init [0-9]+|\-\-grow-stack' | sed 's/^/  /'
  echo '  （若上面为空 ⇒ **两者都没传** ⇒ 用默认）'
done
echo
echo '════ ⑥ 对照：`t5V2`（它出现过多变体）传了什么 ════'
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5V2' | awk '{print $1}'); do
  tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-var-rule [a-z]+|\-\-nuc-init [0-9]+|\-\-nvar [0-9]+|\-\-m [0-9]+' | sed 's/^/  /'
done
