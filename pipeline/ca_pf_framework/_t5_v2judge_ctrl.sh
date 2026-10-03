#!/bin/bash
# _t5_v2judge_ctrl.sh --- ★ 判决器的**双向正/负对照**（本 goal 硬要求：正对照必须能失败）
#
# ## 为什么要它
# 判决器刚修好闸门，现在 V2 只有 11 个事件 ⇒ 四项都显示"⏳ 未到"。
# **但"永远显示未到"本身就是一个**恒真量具****（P26/P43 的同类陷阱）。
# ⇒ 必须证明**闸门能开、且开了之后能给出 PASS 或 FAIL**。
#
# ## 做法（**不改原脚本，用 sed 生成两份对照副本来跑**）
#   正对照（应**开闸**）：把 V 臂换成 `t5H3`（它 24 个事件 ≥ K=23 ⇒ 闸应开）
#   ⇒ 期望：不再显示"未到"，而是逐项给出 ✅/❌
#   负对照（应**关闸**）：把 V 臂换成 `t5V2`（11 个事件 < 23）
#   ⇒ 期望：四项都"⏳ 未到"
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ 正对照：把 V 臂换成 t5H3（24 事件 ≥ K=23 ⇒ 闸**应开**，应出现 ✅/❌）════'
sed "s/res\['t5V2'\], res\['t5H3'\]/res['t5H3'], res['t5H3']/" _t5_v2judge.sh > /tmp/_jd_pos.sh
bash /tmp/_jd_pos.sh 2>&1 | sed -n '/分辨力闸/,/结论/p' | head -12
echo
echo '════ 负对照：原样（V2 的 11 事件 < 23 ⇒ 闸**应关**，应全"未到"）════'
bash _t5_v2judge.sh 2>&1 | sed -n '/分辨力闸/,/结论/p' | head -12
echo
echo '════ 判据（**预先写死**）════'
P=$(bash /tmp/_jd_pos.sh 2>&1 | grep -c '✅ PASS\|❌ FAIL')
N=$(bash _t5_v2judge.sh 2>&1 | grep -c '⏳ 未到')
echo "  正对照里 ✅/❌ 的项数 = $P  ⇒ $([ "$P" -ge 1 ] && echo 'PASS ✅（闸能开、能给判定）' || echo 'FAIL ❌（闸恒关 ⇒ 恒真量具）')"
echo "  负对照里 ⏳未到 的项数 = $N  ⇒ $([ "$N" -ge 4 ] && echo 'PASS ✅（未到时不下结论）' || echo 'FAIL ❌（未到时仍下结论）')"
