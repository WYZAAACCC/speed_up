#!/bin/bash
# _t5_scver2.sh --- ★★★★★★ 验证第二轮：判据已覆盖 attach+stack+fresh ⇒ 核还会不会溶解？
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5SCW
LOG=_w2_t5_$TAG.log
{
  echo "════ 验证第二轮（判据已覆盖 **attach + stack + fresh** = 100% 通道）════"
  echo "  配置：N=80 · nvar 1 · m 23 · B 1 · steps 700（与 t5SCV 逐项相同，只多两处补丁）"
  echo "  判据（预先写死）："
  echo "   * 出现 supercrit_att / supercrit_stack **拒绝计数** ⇒ 判据生效 ✓"
  echo "   * **Vt 不再在形核事件后下降** ⇒ 核不再出生即溶解 ⇒ **修复确认**"
  echo "   * 若 Vt 仍下降 ⇒ 判据未拦住 ⇒ 需查 probe 的落位/判据阈值"
} >> "$LOG"
$PY -m py_compile windowB_surface.py && echo "  ✅ 语法 OK" >> "$LOG" || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }
echo "  改后 sha256 = $($PY -c "import hashlib;print(hashlib.sha256(open('windowB_surface.py','rb').read()).hexdigest()[:16])")" >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 1 --m 23 --B 1 --steps 700 \
    --cores 0-3 --mem-limit-gb 5.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 260
{
  echo "  ── 260 s 后 ──"
  echo "  进程 = $(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- "--tag $TAG")"
  echo "  ── 形核事件（模式分布）──"
  grep -E '模式 \*\*' _w2_t5_short_$TAG.log 2>/dev/null | tail -6 | cut -c1-190
  echo "  ── Vt 轨迹（判据：**不再在事件后下降**）──"
  grep -E '^\s*\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -6 | cut -c1-120
  echo "  ── 判据拒绝计数（若有）──"
  grep -nE 'supercrit_att|supercrit_stack|sc_att_pass|sc_stack_pass' _w2_t5_short_$TAG.log 2>/dev/null | tail -6 | cut -c1-160
} >> "$LOG"
