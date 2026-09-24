#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
echo "--- 关键锚点:"
grep -n 'capture="envelope"' ca3d.py | head -3
grep -n 'def _ensure_Lg\|def grow_envelopes\|def envelope_sup\|def capture_ratio\|lg_percentile' ca3d.py | head -8
echo "--- 行数:"; wc -l ca3d.py
echo "--- 语法检查:"
/root/miniconda3/envs/ml/bin/python - <<'EOF'
import ast, io
s = io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py", encoding="utf-8").read()
ast.parse(s)
print("syntax OK, lines =", s.count(chr(10))+1)
import sys; sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import ca3d
c = ca3d.CA3D(4,4,4,1e-6)
print("import OK; capture =", c.capture, "; lg_percentile =", c.lg_percentile)
EOF