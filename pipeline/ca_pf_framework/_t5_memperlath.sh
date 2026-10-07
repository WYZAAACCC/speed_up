#!/bin/bash
# _t5_memperlath.sh --- ★★★ 内存与板条数的关系（**实测 + 代码口径**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 两臂的实测峰值 RSS 与 nv ════'
echo '  （两臂都是 N=160 / nv=72；看它们 RSS 与"每场"的关系）'
for t in t5H3 t5V2; do
  R=$(grep -oE '峰值 ?RSS[^0-9]*[0-9.]+ ?GB|RSS=[0-9.]+' _w2_t5_short_$t.log 2>/dev/null | tail -1)
  printf '  %-5s nv=72  %s\n' "$t" "${R:-（日志无记录）}"
done
echo
echo '════ ② 引擎/审计里"每场每胞"的内存口径（找现成结论，按第 22 条纪律）════'
grep -rn "B/胞\|每场\|0\.16 GB\|bytes/cell\|nv_max" _r579_report.py _r579_memlaw* 2>/dev/null | head -6 | cut -c1-140 | sed 's/^/  /'
grep -rn "a = \|c = \|nv_max" R581_T5_RESTART.md 2>/dev/null | head -6 | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ③ 直接算：N³ × 每场字节 ════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
N = 160
n3 = N**3
print('  N=%d ⇒ N³ = %d 胞（盒 = %.2f µm，dx=62.5 nm）' % (N, n3, N*62.5/1000))
for b in (8, 16, 24, 32, 40, 48):
    print('    每场 %2d B/胞 ⇒ 每场 %6.1f MB ⇒ nv=72 时 %6.2f GB ｜ nv=276 时 %6.2f GB'
          % (b, n3*b/1048576, 72*n3*b/1073741824, 276*n3*b/1073741824))
print()
print('  ★ 反过来：把盒缩到 5 µm（N=80）')
N2 = 80; n2 = N2**3
for b in (40,):
    print('    N=80（5.00 µm）每场 %2d B/胞 ⇒ 每场 %5.1f MB ⇒ nv=276 只用 **%.2f GB**'
          % (b, n2*b/1048576, 276*n2*b/1073741824))
PYEOF
