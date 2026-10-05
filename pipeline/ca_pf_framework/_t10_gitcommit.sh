#!/bin/bash
cd /mnt/f/speed_up || exit 1
# ★ 只显式列出本会话的 19 个产出（**绝不 git add -A**；那会吃掉 33 GB 数据）
FILES="
pipeline/ca_pf_framework/_t10_auto_253.sh
pipeline/ca_pf_framework/_t10_c7.sh
pipeline/ca_pf_framework/_t10_c8.sh
pipeline/ca_pf_framework/_t10_c9.sh
pipeline/ca_pf_framework/_t10_c11.sh
pipeline/ca_pf_framework/_t10_c12.sh
pipeline/ca_pf_framework/_t10_c14.sh
pipeline/ca_pf_framework/_t10_c15.sh
pipeline/ca_pf_framework/_t10_c16.sh
pipeline/ca_pf_framework/_t10_commit60.sh
pipeline/ca_pf_framework/_t10_gitstat.sh
pipeline/ca_pf_framework/_t10_gitsort.sh
pipeline/ca_pf_framework/_t10_sw_fix.sh
pipeline/ca_pf_framework/_t10_swapalert_253.sh
pipeline/ca_pf_framework/_t10_watch2.sh
pipeline/ca_pf_framework/_w2_t10_banner.done
pipeline/ca_pf_framework/_w2_t10_seven.done
pipeline/ca_pf_framework/_w2_t10_exit_253_1005_0328.txt
pipeline/ca_pf_framework/_w2_t10_exit_stale_thr4.txt
"
echo "=== 逐个核对存在性 ==="
OK=1
for f in $FILES; do
  if [ -f "$f" ]; then echo "  ✓ $f"; else echo "  ❌ 缺 $f"; OK=0; fi
done
[ "$OK" -eq 1 ] || { echo "有缺文件 ⇒ 中止"; exit 1; }
echo
git add $FILES
echo "=== 暂存区（应恰为上列文件）==="
git diff --cached --name-only
echo
echo -n "  暂存文件数 = "; git diff --cached --name-only | wc -l
echo
git commit -q -F - <<'MSG'
chore(git): 收尾提交本会话剩余产出（19 个文件，全部为脚本/运行标记）+ 记录未跟踪数据体的规模

背景：用户要求「将当前的状态 git 到本地」。核对结果：
· `git diff --name-only` = 0 ⇒ **本会话所有代码与文档改动此前已逐阶段提交**（R602/R603/R604/R605/R606、各 `_t5_patch_*.py`、`windowB_surface.py`/`_bk_exp.py`/`_t5_short.py` 的补丁与备份、各 `_t10_*.py/sh` 分析工具）；
· 未跟踪 = **16,852 个文件 / 约 33 GB**（`npz` 5133、`csv` 5032、`py` 2475、`json` 1715、`sh` 787 …），其中 **15,497 个在 `pipeline/` 下**，另有 `lit/`(603)、`_litcheck/`(256)、`_verify_tmp/`(147)、`lit_search/`(69)、`.litsearch/`(60) 等**更早会话的遗留**。
⇒ **按本仓纪律「绝不 git add -A」**：**33 GB 的算例数据/文献缓存不得入库**（会毁掉仓库）。本次**只显式列出本会话的 19 个产出**提交，其余未跟踪体**保持不动**，待后续用 `.gitignore` 收口（另议）。

本次入库内容：`_t10_c7/c8/c9/c11/c12/c14/c15/c16.sh`、`_t10_commit60.sh`、`_t10_gitstat.sh`、`_t10_gitsort.sh`、`_t10_sw_fix.sh`、`_t10_swapalert_253.sh`、`_t10_auto_253.sh`、`_t10_watch2.sh`（均为此前各阶段的提交/状态/守望脚本），以及 4 个运行标记 `_w2_t10_banner.done`、`_w2_t10_seven.done`、`_w2_t10_exit_253_1005_0328.txt`、`_w2_t10_exit_stale_thr4.txt`。
MSG
git log --oneline -1
echo
echo "=== 提交后复核 ==="
echo -n "  已跟踪但改动 = "; git diff --name-only | wc -l
echo -n "  未跟踪        = "; git ls-files --others --exclude-standard | wc -l
