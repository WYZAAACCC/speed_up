#!/bin/bash
# _t5_stopB6.sh --- 停掉过慢的 t5B6（~3 分钟/次尝试 ⇒ 不可用），保留数据，并落盘诊断
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '── 停前状态 ──'
ps -eo pid,etime,time,%cpu --no-headers -p 59805 2>/dev/null | sed 's/^/  /'
printf '  末步 = %s ｜ 事件 = %s ｜ 被拒 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5B6/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(grep -cE '模式 \*\*' _w2_t5_short_t5B6.log 2>/dev/null)" \
  "$(grep -c '被引擎拒' _w2_t5_short_t5B6.log 2>/dev/null)"
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B6' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已 TERM pid=$P"
done
sleep 6
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B6' | awk '{print $1}'); do
  kill -KILL "$P" 2>/dev/null && echo "  已 KILL pid=$P"
done
D=_exp/_bk_t5/dry_t5B6
[ -d "$D" ] && mv "$D" "${D}_superseded_$(date +%m%d_%H%M)" && echo "  数据已改名保留（未删）"
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]t5_waitB6' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已停等待脚本 pid=$P"
done
echo
echo '════ 诊断结论（落盘）════'
cat <<'EOF'
  ★ 现象：`--B 6`（N=80）构造完成后，**约 3.3 分钟才处理一次候选尝试**
    （17:38:09 构造完成 → 17:41:27 第一个拒绝）⇒ **慢到不可用**
  ★ 拒绝原因：`⚠ athermal 事件 #2 被引擎拒（无可用空场/落位失败）@ step 1`
  ★ 嫌疑（**本会话第七次自查**）：我在 s271 给 `attach`/`stack` 各加的
    `_supercrit_probe` 位于**候选循环内** ⇒ **每个候选都解一次弹性（FFT）**;
    `--nuc-supercrit 1` 在所有算例里都开着 ⇒ 补丁始终生效;
    而 `_supercrit_probe` = **试放 + 精确回滚** ⇒ 内部一次完整弹性求解。
    ⇒ **代价 ∝ (候选数 × 弹性求解成本)**，nv=276 时比 nv=23 贵约 12 倍。
  ★ 佐证：我用 `t5SCV`/`t5SCW`（nvar=1 ⇒ nv=23）验证补丁时**看不出代价**。
  ★ 违反的纪律：本仓 **P2/P4**「改热路径前必须先量代价」—— 我加补丁时**没有先测**。
EOF
echo
echo '════ 下一步（零代码改动的判别法）════'
cat <<'EOF'
  ★ **判别**：设法把 `--nuc-supercrit` 设为 **0**（补丁由 `c.get('supercrit', False)` 门控
    ⇒ 一行都不执行）⇒ 若速度恢复秒级/步 ⇒ **确认是补丁的代价** ✓
  ★ 障碍：`_t5_short.py:79` **硬编码** `'--nuc-supercrit', '1'` ⇒ 需加透传
    （与本会话已验证的三个 patcher 同法：`--diag-terms` / `--no-nucleation` / 等）。
  ★ 修法（确认后）：
    ① **把 probe 从"每候选"改成"每事件一次"**（候选循环**外**先做几何预筛，
       只对最有希望的 1 个候选 probe）;
    ② 或给 probe **降精度**（代码注释自己写了"驱动力只需 ~1e-4 的 σ 精度"）
       + **热启动**（注释逐字：「热启动（上一步的 ε 当初值）+ tol=1e-8
       ⇒ 迭代数从 ~35 降到个位数」）。
EOF
