#!/bin/bash
# _t5_vfy_s153.sh --- 核实插入 + 提交
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 核实那一条（检查串应带反引号）════'
grep -c 'region` 是什么' R581_T5_RESTART.md | sed 's/^/  含 "region` 是什么" 的次数 = /'
grep -n 'region.*是什么' R581_T5_RESTART.md | head -2 | cut -c1-100 | sed 's/^/  /'
echo
echo '════ ② 结构完好（H1 + 接手须知 + 各节）════'
grep -n '^# \|^## 0' R581_T5_RESTART.md | head -8 | cut -c1-70 | sed 's/^/  /'
echo
echo '════ ③ 提交 ════'
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md pipeline/ca_pf_framework/_t5_patch_s153.py pipeline/ca_pf_framework/_t5_vfy_s153.sh
git commit -F - <<'MSGEOF'
R581-T5R-s153 把本 session(§83-§152)的成果汇总插进「接手须知」

接手须知写在 s100, 而此后 §101-§152 产生了大量结论(判据③达成、判决器、region 语义修正…)
=> 若不补, 新会话会从过时状态出发。

插入内容(一处, H1 之后, 不改已有内容): 两臂配置与作用 / 六条判据的 s153 时点判定 /
判决器入口(_t5_v2judge.sh 已双向验证 + 其对照脚本 + _t5_both.sh) /
本 session 修好的语义问题(region 是场/变体标签非连通标签; band 索引是稀疏的不能直接布尔索引;
nblk_sig vs nblk总; 包围盒口径对相邻场不适用) / 三条预先写死的预测 /
新纪律(第18-21条)。

验证: 含 s153 汇总 / nblk_sig / 第21条 / 接手须知 均为 True;
"region 是什么" 那条是我检查串漏了反引号(表里是 `region` 是什么), 已核实存在。
MSGEOF
git log --oneline -1
