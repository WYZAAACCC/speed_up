#!/bin/bash
# R49 规程 #1：**启动后立刻核对表头**（缺列就当场杀，别等几十分钟）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
CSV=_exp/_bk_mb/dry_mb1s62/series.csv
echo "=== 表头核对: $CSV"
if [ ! -f "$CSV" ]; then echo "  (CSV 还没生成，稍后再看)"; else
  NEED='step dG_tip_p90 dG_side_p90 dG_tip_max v_tip_nabs v_side_nabs v_wide_nabs n_tip n_side n_wide tip_sep_nm side_sep_nm wide_sep_nm box_touch_core E_el_J'
  # ⚠ `csv.writer` 的默认行终止符是 **CRLF** ⇒ `head -1` 会把 `\r` 带进**最后一个**
  #   字段里（实测：`wide_sep_nm^M`）。**必须先 `tr -d '\r'`**，否则会把"表头正常"
  #   误报成"缺列"（第一版就是这么误报的 —— `AGENTS.md §3`「先 head 看原始文本
  #   再写正则」的同类）。
  HDR=$(head -1 "$CSV" | tr -d '\r')
  miss=""
  for c in $NEED; do
    echo "$HDR" | tr ',' '\n' | grep -qx "$c" || miss="$miss $c"
  done
  if [ -z "$miss" ]; then echo "  **PASS**：全部 $(echo $NEED | wc -w) 个必需列都在位"
  else echo "  **FAIL**：缺列:$miss  ⇒ 立刻杀掉重跑"; fi
  echo "  总列数 = $(echo "$HDR" | tr ',' '\n' | wc -l)"
  echo "  行数 = $(wc -l < "$CSV")"
fi
echo
echo "=== 快照（应为 0,40,80,... 密采）"
ls _exp/_bk_mb/dry_mb1s62/ 2>/dev/null | grep -c snap
ls _exp/_bk_mb/dry_mb1s62/ 2>/dev/null | grep snap | tail -3
