#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""windowB_acct.py --- WindowB 引擎的**分块计时 / 计数 / 构造期记账**钩子。

## 为什么要把钩子写进生产代码

`_r561_opfacct.py` 用 monkey-patch 包函数，**只能看到函数的边界**。
实测（`_w2_r572_acct_AFTER_24x64_w4.log`）覆盖率只有 **77.1%**，剩下 **22.9%**
落在 `advance()` **函数体内部**的表达式上 —— 而那是当时最大的**单一未知块**，
比任何已记账的子块都大。

要让那部分可见，唯一的办法是在函数体里留标记。所以本模块进生产代码。

## 关闭时（默认）的代价

`mark(tag)` 关闭时只做 **一次函数调用** 并返回单例 `_NOOP`，`with` 再调
`__enter__` / `__exit__` ⇒ 每个钩子点 ≈ 3 次 Python 调用（~0.2 µs）。
STEP 级钩子点约 600 次/步 ⇒ 约 0.12 ms/步，相对 0.2 s/步 ≈ **0.06%**。
这个数**不靠估算**：`_r576_acct_cost.py` 直接对比"带钩子但关闭"与"完全没有钩子"
两版的单步墙钟，判据写成"配对差值 ≤ 1%"。

## 并行安全

`_geom_k` / `_step_k` / `argmin2` 的 worker 里也有钩子。
**`dict` 的 `d[k] = d.get(k,0)+dt` 不是原子的**（GIL 保证单个字节码，不保证读-改-写）
⇒ 每个线程一个独立累加器（`threading.local` + 注册表），报告时再合并
⇒ **无锁、无丢失**。这一点必须显式做：v1 如果共享一个 dict，并行段的账会**静默偏小**。

## 口径

* `T[tag]` —— 墙钟秒数累加（含被嵌套者）
* `C[tag]` —— 调用次数
* `B[tag] = [秒, 字节]` —— **构造期**（一次性）的耗时与分配字节
* 嵌套关系**不自动推断**（并行段无法用栈推断）⇒ 由报告脚本**静态声明**。
"""

import threading
import time

_perf = time.perf_counter


class _TB(object):
    """单线程累加器。"""
    __slots__ = ('t', 'c', 's', 'corrupt')

    def __init__(self):
        self.t = {}
        self.c = {}
        self.s = {}          # 未结束的 span（按 tag）
        self.corrupt = set()  # 配对坏掉的诊断


_local = threading.local()
_reg = []
_lock = threading.Lock()

_ON = [False]

# ---- ★★ R576：**区间轨迹**（只在 `trace_on()` 时记录）--------------------------
#   动机：顶层块之和与 `adv.total` 之间还差 ~7%（N=48/nv=12 时 10 ms/步），
#   而"差在哪一段"从汇总表里**看不出来**（汇总只给总量，不给位置）。
#   ⇒ 记下每个计时点的 (tag, 进入/离开, 时刻, 线程)，由报告脚本**求区间并集**、
#     再打印**没被任何区间覆盖的空隙**及其前后相邻的 tag ⇒ 直接指到源码位置。
#   ⚠ 只在显式打开时记录（`_TR[0]` 判断是一次 list 索引，关闭时 ~40 ns）。
_TR = [False]
TR = []
_TR_MAX = [200000]

T = {}      # 合并后的墙钟（`totals()` 的缓存，由 `totals()` 刷新）
C = {}      # 合并后的次数
B = {}      # tag -> [秒, 字节]（构造期；单线程，无需分线程）


def _tb():
    b = getattr(_local, 'b', None)
    if b is None:
        b = _TB()
        _local.b = b
        with _lock:
            _reg.append(b)
    return b


class _Noop(object):
    __slots__ = ()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_NOOP = _Noop()


class _Bump(object):
    __slots__ = ('tag', 't0', 'b')

    def __init__(self, tag):
        self.tag = tag

    def __enter__(self):
        self.b = _tb()
        self.b.c[self.tag] = self.b.c.get(self.tag, 0) + 1
        self.t0 = _perf()
        if _TR[0] and len(TR) < _TR_MAX[0]:
            TR.append((self.tag, 0, self.t0, threading.get_ident()))
        return self

    def __exit__(self, *a):
        t1 = _perf()
        self.b.t[self.tag] = self.b.t.get(self.tag, 0.0) + (t1 - self.t0)
        if _TR[0] and len(TR) < _TR_MAX[0]:
            TR.append((self.tag, 1, t1, threading.get_ident()))
        return False


class _BOnly(object):
    """只计时 + 计数，但**在 `with` 之前就已经拿到线程累加器**（省一次 `_tb()`）。

    用于会被调用几十万次的极小钩子点（`_minmod` 之类）。"""
    __slots__ = ('tag', 't0', 'b')

    def __init__(self, tag, b):
        self.tag = tag
        self.b = b

    def __enter__(self):
        self.t0 = _perf()
        return self

    def __exit__(self, *a):
        self.b.t[self.tag] = self.b.t.get(self.tag, 0.0) + (_perf() - self.t0)
        return False


class _BCost(object):
    """构造期计时（一次性；不做零成本优化，因为每进程只跑一次）。"""
    __slots__ = ('tag', 't0')

    def __init__(self, tag):
        self.tag = tag

    def __enter__(self):
        self.t0 = _perf()
        return self

    def __exit__(self, *a):
        r = B.get(self.tag)
        if r is None:
            r = B[self.tag] = [0.0, 0]
        r[0] += _perf() - self.t0
        return False


_BNOOP = _BCost  # 构造期总是记账（一次性，开销无所谓）


def mark(tag):
    """计时 + 计数上下文。关闭时返回单例 `_NOOP`（零分配）。"""
    if _ON[0]:
        return _Bump(tag)
    return _NOOP


def mark_in(tag):
    """同 `mark`，但**提前**绑定线程累加器（微钩子点用；关闭时同样零分配）。"""
    if _ON[0]:
        b = _tb()
        b.c[tag] = b.c.get(tag, 0) + 1
        return _BOnly(tag, b)
    return _NOOP


def tick(tag):
    """只计数。"""
    if _ON[0]:
        b = _tb()
        b.c[tag] = b.c.get(tag, 0) + 1


def span_begin(tag):
    """**无缩进**的计时起点（配 `span_end(tag)`）。

    ★ 为什么需要它：`advance()` 里有些块是**几十行的 if/else**，用 `with` 包起来要
      重排整个块的缩进 —— 在一个 5600 行、被 `_r30_regress.sh` 逐位把守的文件里，
      那是不必要的风险。用"起点 + 终点"两个**单行**标记可以做到**零缩进改动**。

    ★★ 为什么 `span_end` **要求把 tag 再传一次**：v1 用**栈**（`span_begin` 压、
      `span_end` 弹）。而一旦块内抛异常 / 提前 `return`，栈就**少弹一层**
      ⇒ 之后**每一次** `span_end()` 都把时间记到**别人的 tag** 上 ——
      量具静默说谎，而且**看起来完全正常**。改成"按 tag 配对 + 缺配即标记 corrupt"
      ⇒ 坏掉的时候**必须**能看出来（`acct.corrupt()` 非空 ⇒ 报告拒绝下结论）。
    """
    if _ON[0]:
        b = _tb()
        if tag in b.s:
            b.corrupt.add('span_begin 重入未配对: %s' % tag)
        t0 = _perf()
        b.s[tag] = t0
        if _TR[0] and len(TR) < _TR_MAX[0]:
            TR.append((tag, 0, t0, threading.get_ident()))


def span_end(tag):
    """配 `span_begin(tag)`：累加并返回本次耗时（未启用时 None）。"""
    if _ON[0]:
        b = _tb()
        t0 = b.s.pop(tag, None)
        if t0 is None:
            b.corrupt.add('span_end 无配对: %s' % tag)
            return None
        t1 = _perf()
        dt = t1 - t0
        b.c[tag] = b.c.get(tag, 0) + 1
        b.t[tag] = b.t.get(tag, 0.0) + dt
        if _TR[0] and len(TR) < _TR_MAX[0]:
            TR.append((tag, 1, t1, threading.get_ident()))
        return dt
    return None


def trace_on(on=True, cap=200000):
    _TR[0] = bool(on)
    _TR_MAX[0] = int(cap)
    if on:
        del TR[:]


def trace_off():
    _TR[0] = False


def trace_gaps(t_lo=None, t_hi=None, tid=None, top=25, skip=()):
    """把轨迹里**同一线程**的区间求并集，返回未被覆盖的**空隙**（按大小降序）。

    返回 `[(gap_seconds, prev_tag, next_tag, t_start_rel), …]`。

    ⚠⚠ `tid` 默认取 **主线程**（`threading.main_thread().ident`）。
      v1 取的是"事件最多的线程" —— 那是 **worker 线程**（`_geom_k`/`_step_k` 里
      每个 mark 都在 worker 里记一次，事件数远多于主线程）⇒ 求出来的"空隙"是
      worker **等活干**的间隔，报出一个 59 ms 的假空隙（占 52.9%），
      而真正的主线程空隙被淹没。**"事件最多的线程"是个错误的默认值。**
    """
    import threading as _th
    ev = list(TR)
    if not ev:
        return []
    if tid is None:
        tid = _th.main_thread().ident
        if not any(e[3] == tid for e in ev):
            from collections import Counter
            tid = Counter(e[3] for e in ev).most_common(1)[0][0]
    ev = [e for e in ev if e[3] == tid]
    ev.sort(key=lambda e: e[2])
    if t_lo is None:
        t_lo = ev[0][2]
    if t_hi is None:
        t_hi = ev[-1][2]
    # 用"进入/离开"配对成闭区间（同一 tag 允许重入 ⇒ 用栈计数）
    open_at = {}
    depth = {}
    ivs = []
    _skip = set(skip)
    for tag, kind, t, _tid in ev:
        if tag in _skip:
            continue
        if kind == 0:
            depth[tag] = depth.get(tag, 0) + 1
            if depth[tag] == 1:
                open_at[tag] = t
        else:
            if depth.get(tag, 0) > 0:
                depth[tag] -= 1
                if depth[tag] == 0:
                    ivs.append((open_at.pop(tag), t, tag))
    ivs.sort()
    # 求并集 + 找空隙
    gaps = []
    cur_end = t_lo
    prev_tag = '<BEGIN>'
    for a, b, tag in ivs:
        if a > cur_end + 0:
            gaps.append((a - cur_end, prev_tag, tag, cur_end - t_lo))
        cur_end = max(cur_end, b)
        prev_tag = tag
    if t_hi > cur_end:
        gaps.append((t_hi - cur_end, prev_tag, '<END>', cur_end - t_lo))
    gaps.sort(key=lambda g: -g[0])
    return gaps[:top]



def corrupt():
    """返回所有"标记配对坏了"的诊断（空列表 = 干净）。

    ★ 两类都要报：① `span_end` 找不到配对；② 跑完还剩**没关闭**的 span
      （`b.s` 非空 —— 说明某处 `span_begin` 之后**提前 return / 抛异常**了）。
      只报①是不够的：`_r576_check.sh` 的 C5 正对照就是"故意只 begin 不 end"，
      第一版 `corrupt()` 对它返回 `[]` ⇒ **自检静默通过**，等于没测。
    """
    out = []
    with _lock:
        regs = list(_reg)
    for b in regs:
        out.extend(sorted(b.corrupt))
        out.extend('span_begin 未关闭: %s' % t for t in sorted(b.s))
    return out


def bcost(tag):
    """构造期计时上下文（`with acct.bcost('build.lam'):`）。

    ★ 只在启用时记账 —— 关闭时返回 `_NOOP`，使**默认路径不被任何全局字典写入污染**
      （否则并发构造多个引擎时会有无谓的跨线程写）。"""
    if _ON[0]:
        return _BCost(tag)
    return _NOOP


def bmem(tag, obj):
    """记构造期分配的字节数。`obj` 可以是 ndarray / int / None。"""
    if not _ON[0]:
        return 0
    if obj is None:
        n = 0
    elif isinstance(obj, int):
        n = int(obj)
    else:
        n = int(getattr(obj, 'nbytes', 0))
    r = B.get(tag)
    if r is None:
        r = B[tag] = [0.0, 0]
    r[1] += n
    return n


def enable():
    _ON[0] = True


def disable():
    _ON[0] = False


def enabled():
    return _ON[0]


def reset():
    """清空**所有**累加器（含各线程的），用于分段测量。"""
    with _lock:
        for b in _reg:
            b.t.clear()
            b.c.clear()
            b.s.clear()
            b.corrupt.clear()
    B.clear()
    T.clear()
    C.clear()


def totals():
    """合并各线程累加器 ⇒ 返回 `(T, C)`。

    ★★★ R576 自查抓到的错：v1 直接 `return T, C`（**模块级字典对象本身**），
      而 `reset()` 会 `T.clear()`。调用方写 `T, C = acct.totals()` 之后**再**做一次
      `acct.reset()`（分阶段测量就是这么用的）⇒ 手里的 `T`/`C` **被清空**，
      表现为"所有 tag 都是 0、看起来像引擎没走那条路"。
      **必须返回副本**（`dict(...)`），让调用方拿到的是**快照**。
    """
    t, c = {}, {}
    with _lock:
        regs = list(_reg)
    for b in regs:
        try:
            for k, v in list(b.t.items()):
                t[k] = t.get(k, 0.0) + v
            for k, v in list(b.c.items()):
                c[k] = c.get(k, 0) + v
        except RuntimeError:      # worker 正在改字典 ⇒ 下一轮再读
            pass
    T.clear()
    T.update(t)
    C.clear()
    C.update(c)
    return dict(t), dict(c)
