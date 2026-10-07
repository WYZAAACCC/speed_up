#!/usr/bin/env bash
# R491 —— 本轮收尾自检
set -u
cd "$(dirname "$0")"
echo "=== 1. 制表符检查 ==="
for f in R488_THREADSCALE.md R489_GPU_VERDICT.md R2_PARAM_VERDICTS.md R481_NUC_SITES.md; do
  [ -f "$f" ] && printf '  %-26s tabs=%s lines=%s\n' "$f" "$(grep -cP '\t' "$f")" "$(wc -l < "$f")"
done

echo
echo "=== 2. 本轮关键数字 ==="
for n in "2.52" "1.493" "0.406" "1200" "1.5 次往返" "CUDA_PATH" "nvidia-cuda-nvrtc" "7910"; do
  c=$(grep -rlF -- "$n" R488_THREADSCALE.md R489_GPU_VERDICT.md 2>/dev/null | tr '\n' ' ')
  if [ -n "$c" ]; then s="OK  ($c)"; else s="MISS"; fi
  printf '  %-16s %s\n' "$n" "$s"
done

echo
echo "=== 3. 在跑的仿真 ==="
ps -eo pid,etimes,pcpu,args --sort=-pcpu | grep -E '[_]bk_exp' | cut -c1-70

echo
echo "=== 4. abA 进度 ==="
[ -f _exp/_bk_mb/dry_abA/series.csv ] && tail -1 _exp/_bk_mb/dry_abA/series.csv \
  | awk -F, '{printf "  step=%s t_s=%.6e Vt=%.4e nreg=%s\n",$1,$2,$6,$8}'

echo
echo "=== 5. GPU 可用性复查 ==="
export CUDA_PATH=/root/miniconda3/envs/ml/lib/python3.12/site-packages/nvidia/cu13
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
try:
    import cupy as cp
    print('  ✅ cupy', cp.__version__, ' 设备:', cp.cuda.runtime.getDeviceProperties(0)['name'].decode())
except Exception as e:
    print('  ❌', repr(e)[:120])
PYEOF

echo
echo "=== 6. 资源 ==="
free -g | head -2
uptime
