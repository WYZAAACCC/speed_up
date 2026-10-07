#!/bin/bash
# _r576_after.sh --- 单跑 AFTER 臂（rfft/einsum/gather），用于调试与取证。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export R561_FFT=rfft R561_EPS0=einsum R561_EDPAIR=gather
export R576_N="${R576_N:-64}" R576_NV="${R576_NV:-24}"
export R576_STEPS="${R576_STEPS:-6}" R576_WORKERS="${R576_WORKERS:-4}"
export R576_OUT="${R576_OUT:-_w2_r576_prof_AFTER_${R576_NV}x${R576_N}_w${R576_WORKERS}.log}"
echo "=== hostfp ==="; $PY _r576_hostfp.py
"$PY" _r576_prof.py
