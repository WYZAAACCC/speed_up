#!/bin/bash
# _t5_patchcost.sh --- ★★★★★★ 判别：我的 supercrit 补丁是否是"极慢"的原因
#
# ## 判别逻辑（**零代码编写，只换文件**）
# * 备份现状（含**两处补丁**）→ `.bak_bothpatches`
# * 还原到 `.bak_stacksc`（**两处补丁都没有**的版本）
# * 用**完全相同的配置**（`--N 80 --B 6`）起一个短程臂
# * **判据（预先写死）**：比较"构造完成 → 第一个形核事件"的**墙钟时间**
#     * 无补丁版 **秒级~十几秒** 而 有补丁版 **~200 s** ⇒ **补丁是原因** ✓
#     * 两者相近 ⇒ **不是补丁** ⇒ 需另找（引擎在 B=6 下的行为）
# * 测完**立刻还原**（把两处补丁装回去），保证生产代码回到本次会话修好的状态
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
S=windowB_surface.py

echo "NOW = $(date '+%F %T')"
echo '── ① 备份现状（含两处补丁）──'
cp -f "$S" "$S.bak_bothpatches" && echo "  已备份 → $S.bak_bothpatches"
$PY -c "import hashlib;print('  现状 sha256 =', hashlib.sha256(open('$S','rb').read()).hexdigest()[:16])"
echo '── ② 确认 .bak_stacksc 是"无补丁"版 ──'
for f in "$S.bak_stacksc" "$S.bak_attachsc" "$S.bak_bothpatches"; do
  [ -f "$f" ] || { echo "  ⚠ 缺 $f"; continue; }
  N1=$($PY -c "print(open('$f',encoding='utf-8').read().count('sc_stack_pass'))")
  N2=$($PY -c "print(open('$f',encoding='utf-8').read().count('sc_att_pass'))")
  SZ=$($PY -c "import os;print(os.path.getsize('$f'))")
  echo "  $f : sc_stack_pass=$N1  sc_att_pass=$N2  大小=$SZ"
done
echo '  ⇒ 目标是找一个 **两个计数都为 0** 的备份（= 无补丁版）'

echo
echo '── ③ 还原到无补丁版并起短程测速臂 ──'
cp -f "$S.bak_stacksc" "$S" && echo "  已还原到 $S.bak_stacksc"
$PY -c "print('  还原后 sc_stack_pass =', open('$S',encoding='utf-8').read().count('sc_stack_pass'),
                 '｜ sc_att_pass =', open('$S',encoding='utf-8').read().count('sc_att_pass'))"
$PY -m py_compile "$S" && echo "  ✅ 语法 OK" || { echo "  ❌ 语法错 ⇒ 立刻还原"; cp -f "$S.bak_bothpatches" "$S"; exit 1; }

TAG=t5NOPATCH
setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 12 --m 23 --B 6 --steps 400 \
    --cores 0-5 --mem-limit-gb 8.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
T0=$(date +%s)
echo "  已起 tag=$TAG（无补丁版）· 开始计时"

# 等到出现第一个形核事件或超时
for i in $(seq 1 40); do
  sleep 15
  NE=$(grep -cE '模式 \*\*' _w2_t5_short_$TAG.log 2>/dev/null)
  STEP=$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)
  if [ "${NE:-0}" -gt 0 ] 2>/dev/null; then
    echo "  ★ **无补丁版**：$(($(date +%s) - T0)) s 内出现第一个形核事件（step=$STEP）"
    break
  fi
  [ $((i % 4)) -eq 0 ] && echo "    [${i}×15s] step=$STEP 事件=$NE"
done
T1=$(($(date +%s) - T0))
echo
echo '════ 判别（**预先写死**）════'
echo "  无补丁版：构造+首个事件 **${T1} s**（事件数=$(grep -cE '模式 \*\*' _w2_t5_short_$TAG.log 2>/dev/null)）"
echo "  有补丁版（t5B6 实测）：构造完成→首个拒绝 **~200 s**，而**一次候选尝试 ~3.3 分钟**"
echo "  ⇒ 若 ${T1} s **远小于 200 s** ⇒ **✅ 确认补丁是"极慢"的原因**"
echo "  ⇒ 若相近 ⇒ ❌ 不是补丁 ⇒ 需另找"

echo
echo '── ④ 停测速臂 + **立刻还原两处补丁** ──'
ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v grep | while read -r PID REST; do
  case "$REST" in *"--tag $TAG"*) kill -9 "$PID" 2>/dev/null; echo "  已停 pid=$PID" ;; esac
done
sleep 3
cp -f "$S.bak_bothpatches" "$S" && echo "  ✅ 已还原到含两处补丁的版本"
$PY -c "print('  还原后 sc_stack_pass =', open('$S',encoding='utf-8').read().count('sc_stack_pass'),
                 '｜ sc_att_pass =', open('$S',encoding='utf-8').read().count('sc_att_pass'))"
$PY -m py_compile "$S" && echo "  ✅ 语法 OK（生产代码已回到修好的状态）"
D=_exp/_bk_t5/dry_$TAG
[ -d "$D" ] && mv "$D" "${D}_superseded_$(date +%m%d_%H%M)" && echo "  测速臂数据已改名保留"
