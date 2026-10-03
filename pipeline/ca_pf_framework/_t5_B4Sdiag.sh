#!/bin/bash
# _t5_B4Sdiag.sh --- ★★★★★★ 起 B4S + `--diag-terms`：**直接测速度律三项**（判溶解由谁驱动）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5B4D
LOG=_w2_t5_$TAG.log
{
  echo "════ B4S + --diag-terms（R208 三项分离诊断）════"
  echo "  配置：N=64 · nvar 1 · m 23 · B 1 ⇒ nv=23 · --no-nucleation · **--diag-terms**"
  echo "  目的：直接读出界面处 |Δdf|（化学）/ |Δed|（弹性）/ |stk·κ|（曲率）的量级，**F1 单列**"
  echo "  判据（预先写死）：若 |Δed| 或 |stk·κ| ≥ |Δdf| ⇒ 是该项把 dG 推负"
} >> "$LOG"
$PY -m py_compile _t5_short.py || { echo "  ❌ 语法错 ⇒ 中止" >> "$LOG"; exit 1; }
echo "  ✅ _t5_short.py 语法 OK" >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 64 --nvar 1 --m 23 --B 1 --steps 800 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --no-nucleation --diag-terms \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 160
{
  echo "  ── 160 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    echo "  ★ argv 核对（应有 --diag-terms 与 --nuc-init 0）:"
    tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-diag-terms|\-\-nuc-init [0-9]+|\-\-grow-stack' | sed 's/^/     /'
  else
    echo "  ⚠ 未找到进程 ⇒ 日志尾部："; tail -6 _w2_t5_short_$TAG.log | cut -c1-150 | sed 's/^/     /'
  fi
  echo "  ── 三项诊断输出（若有）──"
  grep -nE 'diag|三项|Δed|kappa|stk' _w2_t5_short_$TAG.log 2>/dev/null | head -8 | cut -c1-160 | sed 's/^/     /'
} >> "$LOG"
