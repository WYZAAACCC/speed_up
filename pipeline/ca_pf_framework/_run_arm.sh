#!/usr/bin/env bash
# _run_arm.sh —— W0-4：**统一作业启动器 + run manifest**（消灭 `N2` 那类事故）
#
# 为什么需要它（`WINDOWB_STATE_CONFIRMED.md §2 N2`）
# --------------------------------------------------
# 实测事故：三个在跑的 T24 作业对**同一个告警**报出**三个不同行号**（2509 / 2553 / 2563），
# 而当时的文件是 2958 ⇒ 它们 import 了**三份不同的源码**。
# `__pycache__` 只保留最后一份 ⇒ **旧版本不可追回 ⇒ 那三份读数永久作废**。
# 根因：作业启动时**没有记录它跑的是哪个版本**，而引擎在作业运行期间被继续编辑。
#
# 本包装器做三件事
# ----------------
#  ① 启动时把 **引擎与驱动的 SHA256 / mtime / 主机 / 时刻 / 完整命令行** 写进日志头；
#  ② 运行结束后**再取一次 SHA**，若与启动时不同 ⇒ 打一条**醒目警告**，
#     明确写出"本次读数**不可归因于任何单一版本**，不得进入结论"；
#  ③ 全程 `set -u`，并原样传出退出码。
#
# 用法
# ----
#   bash _run_arm.sh <logfile> <arm-name> <python-script> [args...]
# 例：
#   bash _run_arm.sh _w023.log W0-2/W0-3 _probe_drift_ns.py --N 96 --dx-nm 50 --steps 120
#
# 记账
# ----
#  * 本脚本**不改引擎、不改数值**，纯记账。
#  * 它**不负责**"起没起来"的判断 —— 那条纪律是 `ps -eo pid,args | grep -e <脚本名>` **数进程**
#    （`AGENTS.md §3.6` 9p 缓存 + `LIVE_STATE §1` 重复作业陷阱）。
set -u

cd "$(cd "$(dirname "$0")" && pwd)" || exit 90

if [ "$#" -lt 3 ]; then
    echo "用法: bash _run_arm.sh <logfile> <arm-name> <python-script> [args...]" >&2
    exit 64
fi

LOG="$1"; ARM="$2"; shift 2
PY=/root/miniconda3/envs/ml/bin/python
DRIVER="$1"

_sha() { [ -f "$1" ] && sha256sum "$1" | cut -d' ' -f1 || echo "(缺失)"; }
_mt()  { [ -f "$1" ] && stat -c '%y' "$1" || echo "(缺失)"; }

SHA0_ENG=$(_sha windowB_surface.py)
SHA0_DRV=$(_sha "$DRIVER")

{
    echo "=============== RUN MANIFEST ==============="
    echo "arm          = $ARM"
    echo "host         = $(hostname)"
    echo "start        = $(date -Iseconds)"
    echo "cwd          = $(pwd)"
    echo "engine       = windowB_surface.py"
    echo "engine_sha   = $SHA0_ENG"
    echo "engine_mtime = $(_mt windowB_surface.py)"
    echo "driver       = $DRIVER"
    echo "driver_sha   = $SHA0_DRV"
    echo "cmd          = $PY -u $*"
    echo "============================================"
} > "$LOG"

"$PY" -u "$@" >> "$LOG" 2>&1
RC=$?

SHA1_ENG=$(_sha windowB_surface.py)
echo "=============== END ===============" >> "$LOG"
echo "rc           = $RC" >> "$LOG"
echo "end          = $(date -Iseconds)" >> "$LOG"
echo "engine_sha   = $SHA1_ENG" >> "$LOG"

if [ "$SHA0_ENG" != "$SHA1_ENG" ]; then
    {
        echo ""
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "!! ⛔ 引擎在本次运行期间被改动过 —— 读数不可归因于单一版本！"
        echo "!!    启动时 sha = $SHA0_ENG"
        echo "!!    结束时 sha = $SHA1_ENG"
        echo "!!    ⇒ 按 N2 的纪律：**本日志的一切读数不得进入结论**。"
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    } >> "$LOG"
    echo "[_run_arm] ⛔ 引擎 SHA 在运行期间变化：$SHA0_ENG -> $SHA1_ENG" >&2
fi
echo "===================================" >> "$LOG"

exit "$RC"
