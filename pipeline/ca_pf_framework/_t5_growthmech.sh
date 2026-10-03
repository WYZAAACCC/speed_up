#!/bin/bash
# _t5_growthmech.sh --- ★★★★★ 查"生长阶段的伸长机制"：本仓库已有工作 + 当前方程
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 文档里关于"拉长/伸长/长轴生长"的现成结论（第 22 条：先搜文档）════'
grep -rn "拉长\|伸长\|长轴\|elongat\|沿长\|lengthen" *.md 2>/dev/null | head -18 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② `advance()` 的**完整方程**（当前生长项到底是什么）════'
sed -n '3823,3840p' windowB_surface.py | sed 's/^/  /'
echo
echo '════ ③ 速度项 `v_n` 的构造（有没有方向项）════'
grep -n "v_n\|vn =\|_vn" windowB_surface.py | head -14 | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ④ 有没有现成的"各向异性生长/台阶(ledge)"实现 ════'
grep -rn "ledge\|台阶\|growth_aniso\|aniso_growth\|prefer_end\|沿 a 轴" *.py 2>/dev/null | head -14 | cut -c1-150 | sed 's/^/  /'
