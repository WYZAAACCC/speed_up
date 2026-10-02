#!/bin/bash
# _t5_fix1.sh --- ★ 执行修复：停 A 臂（**保留数据 + 可续跑**），起"每变体 12 场"的新臂
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LG=_w2_t5_fix1.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LG"; }

say '════ ① 停 A 臂（tag=t5L62）—— **只 kill，不删任何数据** ════'
# 只杀 tag=t5L62 的那个进程（先按命令行精确定位，避免误伤 B 臂）
APID=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep 'tag t5L62' | awk '{print $1}')
if [ -n "$APID" ]; then
  for p in $APID; do kill -TERM "$p" 2>/dev/null && say "  TERM $p（tag=t5L62）"; done
  sleep 6
  for p in $APID; do kill -9 "$p" 2>/dev/null && say "  KILL $p（仍在则强杀）"; done
else
  say '  ⚠ 没找到 t5L62 的进程（可能已停）'
fi
sleep 3
say '  ── 剩余进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "    pid=%s 已跑=%s\n", $1, $2}'
say "  ── A 臂数据**仍在**（不删）──"
ls -1 _exp/_bk_t5/dry_t5L62/ 2>/dev/null | head -6 | sed 's/^/    /'
du -sh _exp/_bk_t5/dry_t5L62 2>/dev/null | sed 's/^/    /'
say '  ⇒ 之后可用 `--resume _exp/_bk_t5/dry_t5L62/ckpt` **续跑**（已验证逐位相同）'

sleep 5
say '════ ② 起新臂：**nvar=4 / m=12**（nv=48，内存同）════'
say "  内存：$(free -m | awk '/Mem:/{printf "用 %d MB / 余 %d MB", $3, $7}')"
$PY _t5_short.py --tag t5F4 \
   --N 160 --nvar 4 --m 12 --steps 6000 --cores 0-7 --mem-limit-gb 9.5 \
   --overlap-nm 62.5 --every 20 --snap-every 40 --pair-every 50 \
   --ckpt-every 20 --ckpt-keep 2 --archive-old > _w2_t5_fix1_A.log 2>&1 &
NP=$!
say "  ★ 新臂 pid=$NP（tag=t5F4，核 0-7，nvar=4×m=12 ⇒ nv=48）"
say '  ⚠ B 臂（t5L0，overlap=0，核 8-15）**继续跑**，作为 S4 的对照'
sleep 60
say '  ── 60 s 后巡查 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "    pid=%s 已跑=%s\n", $1, $2}'
free -m | sed -n 2p | sed 's/^/    /'
say '=== FIX1 LAUNCHED ==='
