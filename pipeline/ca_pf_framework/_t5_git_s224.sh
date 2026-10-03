#!/bin/bash
# _t5_git_s224.sh --- 提交剂量-响应加点（eng-elong=10）+ 监控扩到 9 臂
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_dose_hi.sh pipeline/ca_pf_framework/_t5_armon.py 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s224 剂量-响应加点(eng-elong=10) + 监控扩到 9 臂

依据(预先写死的判据, §220 判据 2): "若 7 与 5 的差 < 5% => 核的拉长已饱和"。
实测(§222): 7 相对 5 是 4.78 -> 6.66 = **+39%** => 远未饱和 => 判据允许往上试。
=> 起单臂 t5AD_1000(--eng-elong 10.00), 参数与 t5AD_500/700 逐项一致 => 唯一变量 = 剂量。

内存账: 起前用 12779 / 余 11252 MB; 起后 45 s 用 14121 / 余 **9911 MB** => 安全 ✓;
bk_exp 进程数 = 8(四臂 A/B + 剂量 500/700/1000 + t5V2)。
实测: pid=29704 起, 45 s 后存活 ✅ => 该档可用(未触发副作用闸)。

监控扩到 9 臂: TAGS 加入 t5AD_1000 => ['t5AB_A/B/C/D','t5AD_500/700/1000','t5V2','t5H3'];
重启后 pid=29808, 日志含 t5AD_ 的行数 = 22。

判据(预先写死): 1) 长宽比是否继续升(10 > 7?); 2) 若 10 与 7 差 <5% => 饱和点在 7-10 之间;
3) 副作用闸: 若报错(如 elong*R > margin 越界) => 该档不可用; 4) 一致性闸: 本臂 step 0 应仍给 1.86
(种子不受 eng-elong 影响, §222.2) => 若不符说明参数没生效。
MSGEOF
git log --oneline -1
