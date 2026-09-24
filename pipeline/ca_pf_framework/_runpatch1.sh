#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python _patch_step1.py
echo "rc=$?"
echo "--- 锚点:"
grep -n 'capture="envelope"' ca3d.py | head -2
grep -n 'def _ensure_Lg\|def grow_envelopes\|def envelope_sup_vec\|lg_percentile' ca3d.py | head -6
wc -l ca3d.py