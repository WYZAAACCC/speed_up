#!/bin/bash
# _r1_a3facetwatch.sh --- 等 A-3 两臂跑完，自动跑**本轮新建的两个量具**
#
# 为什么单独一个脚本（而不去改 `_r1_a3watch.sh`）
# ------------------------------------------------
# `_r1_a3watch.sh` **正在运行**，而 bash 是**按字节偏移增量读脚本**的
# ⇒ 在执行中改它（尤其改它前面已经读过的部分）可能让它从错位的偏移继续读，
#   执行到垃圾内容。⇒ 新增一个**独立**的观察者，只等 + 只读，互不干扰。
#
# 它补的两个量具是 `_r1_a3watch.sh` **没有**覆盖的：
#   ① `_r1_facetjudge.py` —— **A-3 的核心判决**（从快照 `nhist` 判断有没有长出
#      平坦惯习面：`sharp` 升 且 `mid` 降 ⇒ 造面成功；两臂重合 ⇒ 机制无效）
#   ② `_r1_a3meta.py`    —— **单变量前提**审计（两臂是否只差 `facet_lam`）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1a3facet.log
A=a3_facet00
B=a3_facet04
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

running () { pgrep -f "_r1_exp.py --out _exp/$1" > /dev/null 2>&1; }

for d in "$A" "$B"; do
  log "等 $d **启动**……"
  n=0
  while true; do
    if running "$d" || [ -f "_exp/$d/series.csv" ]; then break; fi
    n=$((n + 1)); [ $((n % 40)) = 0 ] && log "  …仍在等启动（$((n*2/60)) 小时量级）"
    sleep 120
  done
  log "$d 已启动，等它结束……"
  while running "$d"; do sleep 120; done
  log "$d 结束"
done

log "==== A-3 facet 判决（核心）===="
$PY -u _r1_facetjudge.py "$A" "$B" >> "$LOG" 2>&1
log "==== A-3 单变量前提审计 ===="
$PY -u _r1_a3meta.py "$A" "$B" >> "$LOG" 2>&1
log "==== 完成。判读：`sharp` 升+`mid` 降 ⇒ 造面成功；两臂重合 ⇒ 机制在本尺度无效 ===="
