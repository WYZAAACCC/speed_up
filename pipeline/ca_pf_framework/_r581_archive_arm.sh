#!/bin/bash
# _r581_archive_arm.sh <tag> --- 把一个臂的目录 **mv 归档改名**（绝不 rm）
# 用途：杀掉/重跑之前，把已有产物改名留档（goal 硬要求：重跑前一律 mv 归档改名）。
cd "$(dirname "$0")" || exit 1
TAG="${1:?用法: bash _r581_archive_arm.sh <tag> [原因]}"
WHY="${2:-rerun}"
D="_exp/_bk_p2/dry_${TAG}"
if [ ! -d "$D" ]; then echo "  （$D 不存在，无需归档）"; exit 0; fi
TS=$(date +%Y%m%d_%H%M%S)
NEW="${D}_superseded_${WHY}_${TS}"
mv "$D" "$NEW" || { echo "  ❌ mv 失败"; exit 1; }
echo "  ✅ 已归档：$D"
echo "          → $NEW"
echo "  ⚠ **没有删除任何东西**。文件清单："
ls -la "$NEW" | tail -n +2 | awk '{printf "     %-42s %10s B\n", $9, $5}'
