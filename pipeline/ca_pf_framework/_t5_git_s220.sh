#!/bin/bash
# _t5_git_s220.sh --- 提交剂量-响应（2 臂，复用 0/3.75 两个已跑点）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_ab_dose2.sh pipeline/ca_pf_framework/_t5_append_s219.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s220 剂量-响应(2 臂): 复用已跑的 0/3.75 点, 只补 5 与 7

关键节省: 已跑的 A/B 里 t5AB_B 就是 eng-elong=3.75 的剂量点(同 N=80/nvar3/m24/B3/facet0)
=> 剂量-响应只差 5 与 7 => 只需 2 臂(~5 GB), 而非原计划 4 臂(~10 GB, 会到 21 GB 逼近 22 GB 上限
=> 有 AGENTS.md §3.12 的卡死风险)。这是"复用已有数据"省下来的内存。

设计(预先写死): 剂量点 0=t5AB_A(已跑) | 3.75=t5AB_B(已跑) | 5=t5AD_500 | 7=t5AD_700;
参数与 t5AB_* 逐项一致(N=80/nvar3/m24/B3/1400步/cores0-3/overlap62.5/facet-proj 0)
=> 唯一变量 = --eng-elong。

判据(预先写死): 1) 长宽比应随 eng-elong 单调上升; 2) 若 7 与 5 差 <5% => 核的拉长已饱和
(与 §212 一致: 生长阶段不拉长 => 最终比例 ≈ 核的比例); 3) 任一新臂报错或场数骤减 => 该档不可用;
4) 时序闸(第28条): 只认同一末步 + >=3 个步点的趋势。

实测: 起前余 13333 MB => 起后 60 s 用 12918 / 余 11114 MB => 仍余 11 GB, 安全 ✓;
bk_exp 进程数 = 7(四臂 A/B + 2 剂量 + t5V2)。
MSGEOF
git log --oneline -1
