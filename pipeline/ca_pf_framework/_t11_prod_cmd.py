#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_prod_cmd.py —— 构造**生产配置**的 `_bk_exp.py` 命令（参数从 `t10B9` 的 `exp_args` 回读）。

## 为什么要它
  `_t5_short.py` 的 `SWITCHES` 是**写死的 13 项**，**没有透传口子** ⇒
  无法加 `--pf-phi onfly`（而它按 `AGENTS.md` 记账约能省 ~11 GB @N=160/nv=220）。
  `t10PROD1` 已因**内存看门狗**被杀（`VmHWM=20.18 GB > 20 GB 上限`）。
  ⇒ 直调 `_bk_exp.py`，参数**从生产算例自己的 `meta.json` 回读**（硬步骤 A）。

用法:
  _t11_prod_cmd.py --print                 # 只打印命令
  _t11_prod_cmd.py --run --tag X [覆盖...]  # 直接跑
"""
import argparse
import json
import os
import subprocess
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
PY = "/root/miniconda3/envs/ml/bin/python"
SRC = "dry_t10B9"          # 参数来源（生产算例）
ROOT = os.path.dirname(os.path.abspath(__file__))


def load_src():
    d = next((os.path.join(b, SRC) for b in BASES
              if os.path.exists(os.path.join(b, SRC, "meta.json"))), None)
    if d is None:
        sys.exit(f"**找不到 {SRC}/meta.json**")
    m = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
    return m, (m.get("exp_args", {}) or {})


def build(over):
    """★ 2026-10-06 **重写**：从"手抄键清单"改为**整个 `exp_args` 全量透传**。

    ## 为什么要改（我犯的错，留档）
      第一版我**手抄了 40 多个键**逐项回读。结果漏掉 **`burst_km`** ——
      而它控制 `_n_blk` 的算式与 `_rej_cap`：
        `burst_km != 0` ⇒ `_n_blk = round(23·f_KM(849)) = 15` ⇒ `_tgt = 9×15 = 135`
        `burst_km == 0` ⇒ `_n_blk = floor(α·(Ms−849)) = 1`  ⇒ `_tgt = 9×1  = 9`
      ⇒ 生产跑 `t10PROD1` 的档目标被**钉死在 9**（与用户 ⑧ 的「两百多根」冲突）。
      ⚠ **教训**：手写键清单的"逐项回读"**不是逐项** ⇒ 必须**全量透传**，
        只显式覆盖**明确要改**的那几项。
    """
    m, ea = load_src()
    import _t11_argparse_meta as AM
    META = AM.build_meta()
    # ★ 规范化名 → 注册名（**必须做**：`exp_args` 是下划线名 `T_end`，
    #   而 `add_argument('--T-end')` 注册的是 `T-end`；且 `_bk_exp.py` 里
    #   **两种拼法都有**（如 `--dry_run` 与 `--cool-rate` 并存）
    #   ⇒ 只按一种拼法查表会**漏掉大半参数**，所以建归一化映射。
    NORM = {}

    def _norm(x):
        return str(x).lstrip('-').replace('_', '-').lower()

    for k in META:
        NORM.setdefault(_norm(k), k)
        for al in META[k].get('aliases', []):
            NORM.setdefault(_norm(al), k)

    # `exp_args` 的值 → CLI 字符串（bool 转 0/1；其余 str）
    def s_(v):
        if isinstance(v, bool):
            return '1' if v else '0'
        return str(v)

    def emit(argv, key, v):
        """按 **argparse 源码派生的元信息** 决定怎么发一个参数（**不手写清单**）。

        ⚠ 四个坑（我全踩过，见 `_t11_argparse_meta.py` 的说明）：
          1. **开关型**（`store_true`）**不能带值** ⇒ 只发 `--key`；
          2. **空串**会被 argparse 当"没给值" ⇒ **吞掉后面的 token**
             （实测 `error: unrecognized arguments: 0 0 0 1 …`）⇒ **跳过空串**；
          3. 键不在解析器里 ⇒ 不发（`_bk_exp.py` 会拒未知参数）；
          4. **下划线/连字符两种拼法**都要能查到 ⇒ 走 `NORM` 归一化。
        """
        reg = key if key in META else NORM.get(_norm(key))
        if reg is None:
            argv.append('#' + key + '=NOT_IN_PARSER')      # 留痕，便于自查
            return
        if META[reg]['flag']:
            if v in (True, 1, '1', 'true', 'True'):
                argv.append('--' + reg)
            return
        if v is None or (isinstance(v, str) and v.strip() == ''):
            return                                          # 坑 2：跳过空串
        argv += ['--' + reg, s_(v)]

    EXCL = {'tag', 'out'}                     # 输出位置必须由本脚本决定
    # ★★ 我犯的错（留档）：`EXCL` 把 `out` 从**全量透传**里排除，
    #   而 `over` 里**只有 `tag`** ⇒ `--out` **两边都漏** ⇒ 引擎用解析器默认
    #   `_exp/_bk_block`（**不是** `t10B9` 的 `_exp/_bk_t5`）
    #   ⇒ 生产跑一整轮都写错目录（实测 `_t11_check_cmd.py` 报 `--out` 出现 **0** 次）。
    #   ⇒ **修法**：凡在 `EXCL` 里的键，**必须**在 `over` 里有确定值，否则**硬失败**。
    for _k in EXCL:
        if _k not in over:
            raise SystemExit(
                '❌ `%s` 在 EXCL 里但 `over` 里没有值 ⇒ 它会**两边都漏**、'
                '静默用解析器默认值。必须在 `over` 里给确定值。' % _k)
    argv = []
    for k in sorted(ea):
        if k in EXCL or k in over:
            continue
        emit(argv, k, ea[k])
    # 显式覆盖项也**必须走同一套归一化**（坑 4 的同一个坑）：
    #   `--pf-phi` 在解析器里注册为**连字符**，若这里拼成 `--pf_phi`
    #   ⇒ argparse 报 `unrecognized arguments`。
    for k in sorted(over):
        reg = k if k in META else NORM.get(_norm(k), k)
        argv += ['--' + reg, s_(over[k])]
    # ---- 自查（不通过就硬失败，不再靠"我记得传了"）----
    _miss = [x for x in ('out', 'tag')
             if ('--' + x) not in argv]
    if _miss:
        raise SystemExit('❌ 生成的自查失败：命令里缺 %s' % _miss)
    cmd = [PY, "-u", "_bk_exp.py"] + argv
    nv = int(ea.get("nv", m.get("nv", 220)))
    n_l = len(str(ea.get("laths", "")).split(',')) if ea.get("laths") else nv
    return cmd, nv, n_l


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--print', dest='doprint', action='store_true')
    ap.add_argument('--tag', default='t10PROD2')
    ap.add_argument('--steps', type=int, default=None)
    ap.add_argument('--pf-phi', default=None)
    ap.add_argument('--ckpt-every', type=int, default=None)
    ap.add_argument('--mem-limit-gb', type=float, default=None)
    a = ap.parse_args()
    over = {k: v for k, v in (('steps', a.steps), ('pf_phi', a.pf_phi),
                              ('ckpt_every', a.ckpt_every)) if v is not None}
    over['tag'] = a.tag
    # ★ `--out` **必须显式给**（见 `build()` 里的留档：漏它会让引擎静默用默认目录）
    over.setdefault('out', '_exp/_bk_t5')
    cmd, nv, nl = build(over)
    print(f"参数来源 = {SRC}/meta.json（回读）  nv={nv}  laths={nl} 个")
    print("\n命令：")
    print('  ' + ' '.join(cmd))
    if a.doprint or not a.run:
        sys.exit(0)
    log = "/mnt/f/speed_up/_w2_%s.log" % a.tag
    print(f"\n运行中 → {log}")
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    print(f"退出码 = {rc}")
    tail = subprocess.run(["tail", "-10", log], capture_output=True, text=True)
    print(tail.stdout)
