#!/bin/bash
# _t5_smoke_stack.sh --- ★★★★★ 冒烟测试：验证 `stack` 现在**真的建新场**
#
# ## 判据（**预先写死**）
# 跑一个小算例（N=64，nv 足够，~300 步），然后看 `nuc_dbg.json` 的 `T_events`：
#   * **每个 mode=stack 的事件，其 `field` **不应**等于同 step 内 attach 事件的场号**；
#   * 更硬的判据：**不同场号数 / 事件数 应接近 1**（修复前是 19/34 = 0.56）；
#   * 且 **`nslab_n` 应显著高于修复前同 step 的值**。
#
# ⚠ 只用小盒子（N=64 ⇒ 4 µm）与少量步数 ⇒ 几分钟出结果，不占机器。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5FIX
LOG=_w2_t5_$TAG.log

echo "[$(date '+%F %T')] ════ 冒烟测试（验证 stack 建新场）════" | tee -a "$LOG"
echo "[$(date '+%F %T')]   物理基线 abA · N=64 · nvar 4 · m 8 ⇒ nv=32 · steps=400 · eng-elong 7" | tee -a "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 64 --nvar 4 --m 8 --B 2 --steps 400 \
    --cores 0-3 --mem-limit-gb 4.0 --every 20 --snap-every 40 --pair-every 100 \
    --eng-elong 7.00 --overlap-nm 62.5 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
sleep 20
echo "[$(date '+%F %T')]   已起（pid 见下）" | tee -a "$LOG"
ps -eo pid,args --no-headers 2>/dev/null | grep "[_]bk_exp.py" | grep -- "--tag $TAG" | cut -c1-90 | tee -a "$LOG"
