#!/bin/bash
# _r581_qhealth.sh --- 查队列还活着吗（它必须活到两臂结束才起 m=12 的两臂）
cd "$(dirname "$0")" || exit 1
echo '=== 1. 队列脚本进程 ==='
n=$(ps -eo args --no-headers 2>/dev/null | grep '_r581_mqueue\.sh' | grep -vc grep)
echo "  _r581_mqueue.sh 进程数 = $n"
echo
echo '=== 2. 它派生的子进程（应为 0：还在 sleep 循环）==='
ps -eo pid,args --no-headers 2>/dev/null | grep '_r581_p2\.py' | grep -v grep | sed 's/^/  /'
echo
echo '=== 3. 在跑的 worker（按 tag，取 RSS 最大的那条）==='
ps -eo pid,rss,args --no-headers 2>/dev/null | grep '_bk_exp\.py' | grep -v grep \
  | awk '{tag=""; for(i=1;i<=NF;i++) if($i=="--tag") tag=$(i+1); if(tag!="") printf "  %-9s pid=%-8s rss=%.2f GB\n", tag, $1, $2/1048576}'
echo
echo '=== 4. 内存 ==='
free -m | sed -n '2p' | sed 's/^/  /'
echo
echo '=== 5. 队列要等的两个 tag（它们的 series 行数）==='
for t in p2_b5ov p2_b5ps; do
  f="_exp/_bk_p2/dry_${t}/series.csv"
  if [ -f "$f" ]; then
    printf '  %-9s series=%-5s 末step=%s\n' "$t" "$(wc -l < "$f")" "$(tail -1 "$f" | cut -d, -f1)"
  fi
done
