#!/bin/bash
# _r1_fjctl.sh --- `_r1_facetjudge.py` 的 **F-4 两臂判决逻辑**负对照
# 做法：把同一个臂的**同一份数据**复制成一个"另一臂"
#   ⇒ 两臂必然完全一致 ⇒ F-4 应走"**两臂几乎一致 ⇒ 该机制在本尺度不起作用**"那一支。
# 目的：验证**空结果分支**真的会被触发（A-2 论证提示"机制无效"是**很可能**的结局，
#       若那一支有 bug，就会把"无效"误报成"有效"）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
rm -rf _exp/_fj_ctrl
cp -r _exp/a3_facet04 _exp/_fj_ctrl
echo "=== 负对照：同一份数据当两臂 ==="
$PY -u _r1_facetjudge.py a3_facet04 _fj_ctrl 2>&1 | tail -12
echo
echo "=== 正对照：把其中一臂的直方图人为改成"更尖"（造面成功的样子）==="
$PY - <<'PYEOF'
import glob, numpy as np
f=sorted(glob.glob('_exp/_fj_ctrl/snap_*.npz'))[-1]
z=np.load(f)
H=z['nhist'].astype(float)
# 人为把中间格搬到顶格 => 峰更尖、mid 更小 = "造面成功"的签名
H2=H.copy()
H2[7,:]+=H2[2:6,:].sum(0); H2[2:6,:]=0
np.savez_compressed(f, region=z['region'], step=z['step'], t=z['t'],
                    nhist=H2.astype(np.int32))
print('已改写 %s 的 nhist（顶格吸收中间格）'%f)
PYEOF
$PY -u _r1_facetjudge.py a3_facet04 _fj_ctrl 2>&1 | tail -8
rm -rf _exp/_fj_ctrl
