#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
echo "=== verify_ca3d.py 里 scheil 相关:"
grep -n -B4 -A16 'scheil_chemistry' verify_ca3d.py | head -50
echo; echo "=== ca3d.py 里 c / cl 相关的属性:"
grep -n 'self\.c\b\|self\.cl\b\|self\.cl_max\|self\.c_last\|self\.fcap' ca3d.py