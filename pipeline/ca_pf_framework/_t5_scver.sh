#!/bin/bash
# _t5_scver.sh --- ★★★★★★ 验证：`stack` 通道的判据是否真的开始拒绝？（用有 stack 事件的配置）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5SCV
LOG=_w2_t5_$TAG.log
{
  echo "════ 验证 stack 通道的超临界判据（配置同 t5B2：N=80 · nvar 1 · m 23 · B 1）════"
  echo "  改动：windowB_surface.py 的 stack 分支插入 _supercrit_probe（由同一 --nuc-supercrit 门控）"
  echo "  判据（预先写死）："
  echo "   * **出现 `supercrit_stack` 拒绝计数** ⇒ 判据生效 ✓"
  echo "   * 计数为 0 且 stack 全部通过 ⇒ 判据未生效（需查接线）"
  echo "   * 同时报：`sc_stack_last_ed`（放核后 ed）应为**负**、`sc_stack_last_df` 为正"
} >> "$LOG"
$PY -m py_compile windowB_surface.py && echo "  ✅ 语法 OK" >> "$LOG" || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }

setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 1 --m 23 --B 1 --steps 700 \
    --cores 0-3 --mem-limit-gb 5.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 240
{
  echo "  ── 240 s 后 ──"
  echo "  进程 = $(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- "--tag $TAG")"
  echo "  ── 形核事件与判据计数 ──"
  grep -nE '模式 \*\*|supercrit|sc_stack' _w2_t5_short_$TAG.log 2>/dev/null | tail -12 | cut -c1-175
  echo "  ── 场数 / 板条数 ──"
  grep -E '^\s*\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -3 | cut -c1-150
} >> "$LOG"
