#!/usr/bin/env bash
# _run_box24.sh --- 24 µm 盒 / Δx=125 nm（N=192）的**第一次正式使用**
#
# 为什么是这个配置（用户 2026-09-29 指定）
#   4.008 µm 盒只有板条长（8.1 µm）的 **49%** ⇒ 连一根板条都装不下；
#   24 µm / Δx=125 nm 是**现在跑得动、且能装下一整块**的配置（本轮实测 7.47 GB / 39.5 s·步⁻¹）。
#
# 本脚本跑 **Stage-1：单等轴核能不能长成板条**（判据见下）
#   种子用 `_probe_shape.py` 的默认 R=500 / t=700 nm ⇒ 在 Δx=125 下 t/Δx=5.6、R/Δx=4.0（过 R13）。
#   走**等轴核**是刻意的：这是对生长律的**强检验**（片状核会把答案塞进初值）。
#
# 判据（`WINDOWB_DATA_AUDIT_R141.md` §1 已定，四条同时成立才算"长出板条"）
#   ① `A(x)` 截面积剖面出现**平台**（不再单峰）
#   ② `|n·a|>0.9` 界面面积占比 **≥10%**（存在"只沿长度推进"的端面）
#   ③ `fill_n` 向**同分辨率长方体参考**靠拢（不是停在椭球参考附近）
#   ④ 形状比 L:W:T **单调趋向速率比且不停住**
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
echo "########## 24 µm 盒 / Δx=125 nm  Stage-1  start=$(date -Is) ##########"
free -g | head -2

echo ""
echo "===== 冒烟：10 步，确认 N=192 能构造且不 OOM ====="
timeout 1800 "$PY" -u _probe_shape.py --N 192 --dx-nm 125 --steps 10 --every 5 \
    --arms aniso > _w2_box24_smoke.log 2>&1
RC=$?
echo "### 冒烟 rc=${RC}"
if [ "$RC" -ne 0 ]; then
  echo "--- 冒烟失败，尾部："; tail -15 _w2_box24_smoke.log
  echo "########## 中止 ##########"; exit 1
fi
grep -e "步时" -e "胞=" _w2_box24_smoke.log | tail -4

echo ""
echo "===== 长跑：900 步（每 50 步一个采样，共 18 个点，供 R20 回归）====="
timeout 86400 "$PY" -u _probe_shape.py --N 192 --dx-nm 125 --steps 900 --every 50 \
    --arms aniso > _w2_box24_L1.log 2>&1
echo "### 长跑 rc=$? @ $(date -Is)"
echo "########## 结束 ##########"
