#!/usr/bin/env bash
# _quick_t13b.sh --- 快速、带心跳的 T13b 诊断跑：`f_target=0.035`（≈ 碰撞分数 f_imp≈0.033）
#   目的：① 证明整条链能出数；② 量出真实步时；③ 给出第一组 block/厚度读数。
#   若这一步在 ~15 min 内出数，说明之前的长作业只是"采样门槛设太高"，而非卡死。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY - <<'EOF'
import ast
for f in ('T13b_verify_nv.py',):
    ast.parse(open(f).read()); print('SYNTAX OK', f)
EOF
setsid nohup "$PY" -u T13b_verify_nv.py --L-um 4.8 --dx-nm 50 --ns 64,128 \
        --f-target 0.035 --adv proj2 > _t13b_quick.log 2>&1 < /dev/null &
echo "T13bQuick pid=$!"
sleep 20
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-66
