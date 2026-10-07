#!/bin/bash
# _t5_waitfix.sh --- ★★★★★★ 等 `t5FIX` 到 step ≥640，自动做步对齐四项比较（避 9p 陈旧读）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TGT=${1:-640}; LIM=${2:-7200}; T=0
echo "  等 t5FIX 的最大快照 ≥ $TGT（最多 ${LIM} s）"
while [ "$T" -lt "$LIM" ]; do
  S=$(ls -1 _exp/_bk_t5/dry_t5FIX/snap_*.npz 2>/dev/null | sed 's/.*snap_//; s/\.npz//' | sort -n | tail -1)
  S=${S:-0}
  [ "$S" -ge "$TGT" ] 2>/dev/null && { echo "  ★ t5FIX 最大快照 = $S"; break; }
  P=$(ps -eo args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -c -- '--tag t5FIX')
  [ "$P" -eq 0 ] && { echo "  ⚠ t5FIX 进程消失（最大快照 $S）"; break; }
  sleep 120; T=$((T + 120))
done
echo "NOW = $(date '+%F %T')  等了 ${T} s"
echo
echo '════ ★★★ 步对齐四项：对照 vs 修复（同一 step）════'
timeout 1500 $PY _t5_aralign.py 400,480,560,640 2>&1 | sed -n '4,9p'
echo
echo '════ ★ 判据（**预先写死**）════'
cat <<'EOF'
  ★ 对照 `t5N276F` 的宽比：400→6.54 ｜ 480→6.13 ｜ **560→5.11** ｜ **640→4.86** ｜ 终态→**3.28**
    长厚：11.61 ｜ 11.11 ｜ **10.62** ｜ **9.56** ｜ 终态→**6.40**
    瓣中位：1.5 ｜ 2.0 ｜ 2.5 ｜ 2.0 ｜ 终态→**12–13**
  ★ **修法 A 有效的判据**：`t5FIX` 在 **560/640** 上
     · **宽比守住 ~6**（对照 5.11/4.86）⇒ **阻止了退化** ✓
     · **瓣中位远低于对照**（对照 2.5/2.0，终态 12）
     · **单块场比例高于对照**
  ★ **若修复也跟着掉**（如 560 → 5.0、640 → 4.5）⇒ **修法 A 不足以阻止**
     ⇒ 需调 η（0.375 → 0.5/0.6）或查**拥挤机制** ⇒ 迭代
EOF
echo
echo '════ ★ 每档核数（burst 生效）════'
for t in t5FIX t5ETAo t5BKMo t5N276F; do
  printf '  [%-8s] %s\n' "$t" "$(grep -oE 'T=[0-9.]+ K' _w2_t5_short_$t.log 2>/dev/null | sort | uniq -c | head -3 | tr '\n' ' ')"
done
echo
echo '════ ★ 块表（④⑤⑥）════'
for t in t5FIX t5N276F; do
  printf '  [%-8s] %s\n' "$t" "$(tail -2 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | tr '\n' '|' | cut -c1-180)"
done
free -m | sed -n 2p | sed 's/^/  /'
