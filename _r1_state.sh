#!/bin/bash
cd /mnt/f/speed_up || exit 1
echo "=== git ==="
git log --oneline -3
echo "=== git status ==="
git status --porcelain | head -20
echo "=== procs (python) ==="
ps -eo pid,etimes,args | grep -E "python3 |_probe|sim_" | grep -v grep | head -20
echo "=== mem ==="
free -g
echo "=== nproc ==="
nproc
echo "=== framework files ==="
ls -la pipeline/ca_pf_framework/*.py | head -40
