#!/bin/bash
# _t5_seed.sh --- 定位 nuc_cfg 的调用与 seed 参数（为加 --nuc-seed 旋钮），顺带看长跑
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① nuc_cfg 的调用点 ════'
grep -n 'nuc_cfg(' _bk_exp.py windowB_surface.py 2>/dev/null | cut -c1-128 | sed 's/^/  /'
echo
echo '════ ② nuc_cfg 的签名（含 seed）════'
sed -n "$(grep -n 'def nuc_cfg' windowB_surface.py | head -1 | cut -d: -f1),+14p" windowB_surface.py \
  | cut -c1-124 | sed 's/^/  /'
echo
echo '════ ③ 调用点的上下文（看它传了哪些）════'
LN=$(grep -n 'nuc_cfg(' _bk_exp.py | head -1 | cut -d: -f1)
[ -n "$LN" ] && sed -n "$((LN-6)),$((LN+22))p" _bk_exp.py | cut -c1-124 | sed 's/^/  /'
echo
echo '════ ④ 长跑进度 ════'
ps -eo pid,etime,rss --no-headers 2>/dev/null | head -0
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
/root/miniconda3/envs/ml/bin/python _t5_obs.py 2>&1 | grep -E '^  ── t5L|填充分数|末 [0-9]+ 行' | sed 's/^/  /'
