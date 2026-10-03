#!/bin/bash
# _t5_B4S2.sh --- ★★★★★★ 二分实验 B4S（**用新开关**）：只有种子、禁止形核
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5B4S
LOG=_w2_t5_$TAG.log
{
  echo "════ 二分实验 B4S（第 2 次尝试，用新加的 `--no-nucleation`）════"
  echo "  配置：N=64 · nvar 1 · m 23 · B 1 ⇒ nv=23 · **--no-nucleation**（去掉 grow-stack，nuc-init 0）"
  echo "  判据（预先写死）：场 1 的 φ<0 瓣数 1→≥2 ⇒ **演化有责**；恒=1 ⇒ **演化无辜**"
} >> "$LOG"

# 语法自检
$PY -m py_compile _t5_short.py || { echo "  ❌ _t5_short.py 语法错误 ⇒ 中止" >> "$LOG"; exit 1; }
echo "  ✅ _t5_short.py 语法 OK" >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 64 --nvar 1 --m 23 --B 1 --steps 1200 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --no-nucleation \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"

sleep 150
{
  echo "  ── 150 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    echo "  ★ **引擎 argv 核对**（关键：应有 --nuc-init 0，**不应有** --grow-stack）："
    tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null \
      | grep -oE '\-\-nuc-init [0-9]+|\-\-grow-stack|\-\-N [0-9]+|\-\-eng-elong [0-9.]+|\-\-nuc-law [a-z]+' \
      | sed 's/^/     /'
    echo "     ⚠ 若上面**没有** --grow-stack 且有 --nuc-init 0 ⇒ 开关生效 ✓"
  else
    echo "  ⚠ 未找到进程 ⇒ 查日志尾部："
    tail -6 _w2_t5_short_$TAG.log | cut -c1-150 | sed 's/^/     /'
  fi
} >> "$LOG"
