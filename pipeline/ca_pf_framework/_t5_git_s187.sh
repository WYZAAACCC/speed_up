#!/bin/bash
# _t5_git_s187.sh --- 提交 s187 附录
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md pipeline/ca_pf_framework/_t5_patch_s187.py \
        pipeline/ca_pf_framework/_t5_waitv2.sh pipeline/ca_pf_framework/_t5_wait1400.sh
git commit -F - <<'MSGEOF'
R581-T5R-s187 给「接手须知」补 s187 附录 (§164-§185 的重大发现)

为什么必须补: s153 汇总写在 §152, 而此后出现了本 goal 最重要的三条结构性结论,
不补则新会话会以为"只要等就会填满盒子"。

补的内容(一处插入, 接在 s153 汇总之后):
1. 填充被 nv 线性限制: nv=72 => 最多 69 根; 每根 0.2550 µm³; 盒 1000 µm³
   => 理论上限 1.76%, 实测 1.08% 吻合; 要达 abA 的 11.8% 需 ~460 根 => 74 GB => 超出本机 22 GB。
2. 判据⑤ 的读法已被约束唯一确定: (A) 高体积分数无解(与"本机内存"和"盒>=10µm"两条硬约束冲突);
   (B) 影响范围铺满盒子 => 采用。⑤ 的三档观测量与"覆盖判据晚于①②③写死"的记账。
3. ④⑤⑥ 全部依赖 fresh 通道: stack/attach 是 sympathetic(挤在种子上, 实测覆盖仅 3/8、box_touch=0);
   fresh 是唯一能把结构撒开的通道, 而它需要 m 有余量 + --var-rule random => 只有 t5V2 同时具备。
加上: 定量预期(fresh ~5-6 次; B<=3 已到顶)、已验预测(带延伸 0->8->18)、两个等待作业(pwsh-2561/2562)。

验证: 含 s187 附录 / 1.76% / 判据⑤ 的读法 / sympathetic / pwsh-2561 均为 True。
MSGEOF
git log --oneline -1
