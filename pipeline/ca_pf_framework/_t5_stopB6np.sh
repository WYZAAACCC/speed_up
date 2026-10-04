#!/bin/bash
# _t5_stopB6np.sh --- 停 `t5B6np`（线索 A 已由三个对齐点否证）以释放资源给线索 B 实验
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '── 停前 ──'
for t in t5B6np t5BK1; do
  printf '  %-8s 末步=%-6s 事件=%-4s\n' "$t" \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(grep -cE '模式 \*\*' _w2_t5_short_$t.log 2>/dev/null)"
done
echo '── 停掉 t5B6np（数据改名保留，不删）──'
ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v grep | while read -r PID REST; do
  case "$REST" in
    *"--tag t5B6np"*) echo "  KILL pid=$PID"; kill -9 "$PID" 2>/dev/null ;;
  esac
done
sleep 4
D=_exp/_bk_t5/dry_t5B6np
[ -d "$D" ] && mv "$D" "${D}_superseded_$(date +%m%d_%H%M)" && echo "  数据已改名保留"
echo '── 停后引擎进程 ──'
ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v grep | while read -r PID REST; do
  TAG=$(printf '%s' "$REST" | sed -n 's/.*--tag \([A-Za-z0-9_]*\).*/\1/p')
  echo "  pid=$PID tag=${TAG:-?}"
done
echo '── 内存 ──'
free -m | sed -n 2p | sed 's/^/  /'
echo
echo '════ 线索 B 的下一步（**引擎内形状对照**，零解析假设）════'
cat <<'EOF'
  ★ 目的：判"薄板的弹性罚能是否真的比球体**大**"（物理上应**相反** —— 
     Eshelby 理论：薄板惯习面法向自由 ⇒ 罚能应**低于**等轴颗粒）
  ★ 做法（**同 ε⁰、同 C、同盒子，只改形状**）：
     ① 用 `seed_plate` 的**几何参数**（`t` = 厚度、`R` = 半径、`elong`）造两种形状：
        · **薄板**：`t` 小、`R` 大、`elong` 大（现状）
        · **球体**：`t ≈ 2R`、`elong = 1`（各向同性种子）
     ② 各跑一个**短程单根**算例（`--no-nucleation`，N=64，~200 步）
     ③ 直接读 `--diag-terms` 的 **`|Δed|` 中位**（引擎自报，**F1 单列**）
  ★ 判据（**预先写死**）：
     · **薄板 `|ed|` < 球体 `|ed|`** ⇒ **与物理一致** ⇒ 我先前"趋势反常"的判断**作废**
       ⇒ 回到 **Ms/判据**方向（即：是 Ms 与罚能不匹配，而非弹性求解有问题）;
     · **薄板 `|ed|` > 球体** ⇒ **才有资格说"弹性求解没利用薄板几何"** ⇒ 查求解器。
  ★ ⚠ 依据代码注释（`windowB_surface.py` 的 `--nuc-shape`：
     `disc`（默认）= `sdf = max(|d|−t/2, rperp−R)` ⇒ **带尖边圆柱**；
     `ellipsoid` ⇒ 椭球。**两者可切换** ⇒ 用 `--nuc-shape disc/ellipsoid` 也能改形状。
EOF
