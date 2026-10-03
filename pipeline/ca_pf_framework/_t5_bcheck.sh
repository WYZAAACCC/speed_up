#!/bin/bash
# _t5_bcheck.sh --- ★★★★★ 查 B 组（待查项 3/4/6/7）：谁本该抑制厚度生长
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════════ ③ `--facet-proj` / `--facet-excl`：定义、默认、我的取值 ════════'
grep -n "add_argument('--facet-proj'\|add_argument('--facet-excl'" _bk_exp.py | cut -c1-165 | sed 's/^/  /'
echo '  ── 我的启动器传了什么 ──'
grep -n "facet-proj\|facet-excl" _t5_short.py | cut -c1-130 | sed 's/^/  /'
echo '  ── 它们在引擎里怎么用（前 8 处）──'
grep -n "facet_proj\|facet_excl" _bk_exp.py | head -8 | cut -c1-150 | sed 's/^/  /'
echo
echo '════════ ⑥ 界面各向异性：`advance()` 收到的 `aniso`/`npref`/`mob_aniso` ════════'
grep -n "\.advance(" _bk_exp.py | head -8 | cut -c1-160 | sed 's/^/  /'
echo '  ── 那几个实参的**取值来源** ──'
grep -n "aniso=\|npref=\|mob_aniso=" _bk_exp.py | head -12 | cut -c1-150 | sed 's/^/  /'
echo
echo '════════ ④ `elong` 是否也管"生长"（在 advance 路径里出现过吗）════════'
grep -n "elong" windowB_surface.py | head -12 | cut -c1-150 | sed 's/^/  /'
echo
echo '════════ ⑦ 生长项（Allen-Cahn 驱动）有没有**取向偏好** ════════'
grep -n "def advance" windowB_surface.py | cut -c1-120 | sed 's/^/  /'
sed -n '774,812p' windowB_surface.py | sed 's/^/  /'
