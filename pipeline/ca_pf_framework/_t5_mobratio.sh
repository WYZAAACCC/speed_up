#!/bin/bash
# _t5_mobratio.sh --- ★★★★★ `mob_ratio`/`mob_iform`/`mob_wulff` 怎么用 + 是否传给 advance
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 这四个参数的**完整定义段**（含 help：它们是什么物理量）════'
sed -n '3875,3895p' _bk_exp.py | sed 's/^/  /'
echo
echo '════ ② 它们在引擎里被**消费**的地方（传给谁）════'
grep -n "a.mob_ratio\|a.mob_iform\|a.mob_wulff\|a.mob_dip\|mob_aniso=\|mob_ratio=\|mob_iform=" _bk_exp.py | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ③ `advance()` 里 `mob_aniso` / `mob_wulff` 的实际作用（函数体内）════'
grep -n "mob_aniso\|mob_wulff\|mob_dip\|mob_iform\|mob_ratio" windowB_surface.py | head -16 | cut -c1-155 | sed 's/^/  /'
echo
echo '════ ④ kw 那一行的**完整内容**（§212 我读到的是截断的）════'
sed -n '1920,1935p' _bk_exp.py | sed 's/^/  /'
