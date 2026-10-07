#!/bin/bash
# _r1_gatechk.sh --- 验证队列门限 `nactive` 是否被**别的脚本自己的 pgrep 子进程**污染
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 连续 8 次采样（每次间隔 3 s）==="
echo "  nactive 用的是：pgrep -c -f '_r1_exp\\.py'"
echo
for i in $(seq 1 8); do
  n=$(pgrep -c -f '_r1_exp\.py' 2>/dev/null)
  # 真正是 python 算例的（cmdline 以解释器开头）
  real=$(pgrep -c -f '^/root/miniconda3/envs/ml/bin/python -u _r1_exp\.py' 2>/dev/null)
  echo "  poll$i : 旧口径 nactive=${n:-0}   新口径(锚定解释器)=${real:-0}"
  echo "         匹配到的 cmdline 前 60 字："
  pgrep -af '_r1_exp\.py' 2>/dev/null | grep -v "bash -c" | cut -c1-60 | sed 's/^/           /'
  sleep 3
done
echo
echo "⇒ 若旧口径**经常大于**新口径 ⇒ 门限被别的脚本的 pgrep 子进程污染"
echo "   （那会让队列 v6 在'实际只有 1 个算例'时误判为 ≥2 而**空转不启动**）"
