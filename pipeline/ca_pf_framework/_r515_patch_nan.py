#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r515_patch_nan.py —— 把 `_r512` / `_r514` 的**字段比较**改成 **NaN-aware**。

## 自查错误 #101（留痕）

`_r514` 报「`f3_pos_n` / `f3_std_n` **不确定**」⇒ 我一度以为**量具非确定**。
**真相**：那两个字段在两次调用里**都是 `NaN`**（该快照没有 F3 面 ⇒ 位置统计无定义），
而 **`nan != nan`** ⇒ 我的比较函数把它们判成"不同"。

**⇒ 是**我的比较**错，不是量具错。** 量具是确定的。

**⇒ 教训**：比较"量具的可复现性"时**必须先处理 NaN**；
`np.array_equal` 默认 `equal_nan=False`，`==` 对 NaN 恒 False。
**这一条对任何"逐位/逐字段比对"的判据都适用。**
"""
import io

FIXES = [
    ('_r512_oldsnap.py',
     """                if isinstance(a, np.ndarray):
                    if not np.array_equal(a, b):
                        same = False
                        diff.append(k)""",
     """                if isinstance(a, np.ndarray):
                    # ★ #101：NaN-aware（`nan != nan` 会把"两次都是 NaN"误判成"不同"）
                    if not np.array_equal(np.asarray(a, float),
                                          np.asarray(b, float), equal_nan=True):
                        same = False
                        diff.append(k)"""),
    ('_r514_measdet.py',
     """            if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                if not np.array_equal(np.asarray(a), np.asarray(b)):
                    same = False
                    break""",
     """            if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                # ★ #101：NaN-aware
                if not np.array_equal(np.asarray(a, float), np.asarray(b, float),
                                      equal_nan=True):
                    same = False
                    break"""),
    ('_r514_measdet.py',
     """    changed = [k for k in keys if not (
        np.array_equal(np.asarray(ms[0][k]), np.asarray(m2[k]))
        if isinstance(ms[0][k], np.ndarray) or isinstance(m2[k], np.ndarray)
        else (ms[0][k] == m2[k]))]""",
     """    def _eq(a, b):
        \"\"\"★ #101：NaN-aware 相等（两次都是 NaN ⇒ 视为相同）。\"\"\"
        if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
            return bool(np.array_equal(np.asarray(a, float),
                                       np.asarray(b, float), equal_nan=True))
        try:
            af, bf = float(a), float(b)
            if af != af and bf != bf:
                return True                      # 两个 NaN
            return af == bf
        except (TypeError, ValueError):
            return a == b
    changed = [k for k in keys if not _eq(ms[0][k], m2[k])]"""),
]


def main():
    for fn, old, new in FIXES:
        s = io.open(fn, encoding='utf-8').read()
        if new.splitlines()[0].strip() in s and 'equal_nan' in s:
            print('  （%s 已打过，跳过）' % fn)
            continue
        if old not in s:
            print('  ❌ %s：找不到待替换片段' % fn)
            continue
        s = s.replace(old, new, 1)
        io.open(fn, 'w', encoding='utf-8').write(s)
        print('  ✅ %s 已改' % fn)


if __name__ == '__main__':
    main()
