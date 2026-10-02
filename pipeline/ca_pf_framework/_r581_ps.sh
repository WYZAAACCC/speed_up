#!/bin/bash
# _r581_ps.sh --- 列出在跑的长跑臂。**R581-R19 重写**（旧版有两个 bug，留痕）。
#
# ## 旧版的两个 bug（实测，`_r581_postmortem.sh` 抓到的）
# 1. **只 grep `_bk_exp.py`** —— 而我这批臂是用 **`_r581_p2.py --run`** 起的，
#    引擎是**在同一个进程里 import** 的（**没有 `_bk_exp.py` 子进程**）
#    ⇒ 旧版**看不见 p2_b5ov**，于是我把"工具看不见"误读成"**进程消失了**"。
# 2. **同一根臂在 `ps` 里出现两次**（`bash -lc '... --tag p2_b5ov ...'` 的包装进程
#    + 真正的 `python _r581_p2.py ... --tag p2_b5ov ...`）⇒ 旧版**两个都打**，
#    而且 `pid` 可能在两次采样间变化 ⇒ 我盯着一个**包装进程的旧 pid** 看，
#    它一换号我就以为"臂死了"。
#
# ## 新版的纪律
# * 匹配**两种**命令行（`_bk_exp.py` 与 `_r581_p2.py`）；
# * **按 `--tag` 去重**，优先保留**真进程**（argv[0] 是 python 的那条）；
# * **显式打印"我看到几条"**，并且**把"看不到"和"没在跑"分开说**
#   —— 与 `_r581_now.sh`（`ps|grep` 假报两次）**同一类**教训。
set -u
cd "$(dirname "$0")" || exit 1

tmp=$(mktemp)
ps -eo pid,etime,pcpu,rss,args --no-headers 2>/dev/null \
  | grep -E '_bk_exp\.py|_r581_p2\.py' | grep -v grep > "$tmp"

n_raw=$(wc -l < "$tmp")
echo "  （原始匹配 $n_raw 条；按 tag 去重后如下）"
# 按 tag 去重：优先 python 真进程（args 里第 2 个字段含 python）
# ★★ 实测真相（R581-R19）：**每个 tag 有两条 python 进程**
#   * 父：`python _r581_p2.py --run --tag X ...` ⇒ **RSS ~0.01 GB**（只是驱动器）
#   * 子：真正的 worker ⇒ **RSS 4–7 GB**
#   ⇒ 按 **RSS 降序**排，再做 `!seen[tag]++` ⇒ **每个 tag 只留 RSS 最大的那条 = 真 worker**。
#   （旧版把父与子都打，或只看 `_bk_exp.py`，读数随采样时机跳 ⇒ 我误判过"臂消失了"。）
sort -k4 -nr "$tmp" | awk '$5 ~ /python$/ {
  pid=$1; et=$2; cpu=$3; rss=$4; tag=""; ov=""; psd="";
  for(i=5;i<=NF;i++) if($i=="--tag") tag=$(i+1);
  for(i=5;i<=NF;i++) if($i=="--nuc-overlap-nm") ov=$(i+1);
  for(i=5;i<=NF;i++) if($i=="--nuc-periodic-seed") psd=$(i+1);
  if (seen[tag]++) next;
  printf "  tag=%-9s pid=%-7s 跑=%-9s cpu=%-5s rss=%6.2fGB overlap=%-6s periodic=%s\n", \
    tag, pid, et, cpu, rss/1048576, (ov==""?"(默认0)":ov), (psd==""?"(默认0)":psd);
}' 
n_tag=$(awk '$5 ~ /python$/ {for(i=5;i<=NF;i++) if($i=="--tag") print $(i+1)}' "$tmp" | sort -u | wc -l)
echo "  ⇒ 去重后的臂数 = $n_tag"
[ "$n_tag" = 0 ] && echo '  ⚠ **看不到任何臂** —— 注意：这可能只是**匹配串没写对**，不等于「没在跑」。先核对命令行（用 _r581_postmortem.sh）。'
tot=$(awk '{s+=$4} END{printf "%.2f", s/1048576}' "$tmp")
echo "  合计 RSS = ${tot} GB"
rm -f "$tmp"
free -m | sed -n 2p | awk '{printf "  Mem: 已用 %s MB  可用 %s MB\n",$3,$7}'
