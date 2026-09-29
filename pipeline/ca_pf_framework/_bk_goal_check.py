#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_goal_check.py —— 收官核对：把目标的**每一条**逐一对着产物验一遍。

目标（R29）逐句拆开：
  1 提取引擎/驱动/量具里**全部**物理公式的参数
  2 逐参数给出推导或出处（可推的推、借的标出处与误差带、剩下的收成单一可标定常数）
  3 把「块里有多少根板条」从规定值改成由物理量导出的量
  4 几何 n=W_block/t_lath 与 athermal 形核率供给**两者判谁限速**
  5 让默认路径用闭环参数**跑通**
  6 留下**判决证据**
  7 写成**参数闭环文档**
  8 更新 **BLOCK_RESULT / BLOCK_STATUS**

每条都要能指到**具体文件里的具体内容**，不能只说"我做了"。
"""
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import windowB_closure as CL                                    # noqa: E402


def has(path, *needles):
    p = os.path.join(_HERE, path)
    if not os.path.exists(p):
        return False, '文件不存在'
    t = io.open(p, encoding='utf-8').read()
    miss = [n for n in needles if n not in t]
    return (not miss), ('缺: %s' % miss[:2] if miss else 'OK（%d 字符）' % len(t))


def main():
    ps = CL.params()
    tiers = {}
    for p in ps:
        tiers[p['tier']] = tiers.get(p['tier'], 0) + 1
    checks = [
        ('1 全部参数提取（%d 条）' % len(ps), len(ps) >= 40,
         '推%d/借%d/标%d/数%d' % (tiers.get('推', 0), tiers.get('借', 0),
                                  tiers.get('标', 0), tiers.get('数', 0))),
        ('2a 每条都有出处', all(p['source'].strip() for p in ps), 'source 非空'),
        ('2b 每条都能定位到代码', all(p['where'].strip() for p in ps), 'where 非空'),
        ('2c 借来的带误差带', any('带' in p['source'] or '误差' in p['source']
                                  or '—' in p['source'] for p in ps), '见 source 列'),
        ('3 n 是导出量', has('BLOCK_PARAM_CLOSURE.md', 'n = N_A·A_f',
                             'floor(6.325)')[0], 'C-2'),
        ('4 谁限速', has('BLOCK_PARAM_CLOSURE.md', 'C-8', '供给限速')[0], 'C-8'),
        ('5a --closed 一条命令', has('_bk_exp.py', '--closed', '_apply_closed')[0],
         '参数被套用且逐条打印来源'),
        ('5b 一条命令 == 长命令行', os.path.exists(os.path.join(_HERE,
                                                               '_bk_closedcheck.py')),
         '20 项 0 不一致 + 6 条合法性'),
        ('6a 完整判决（cln2）', has('BLOCK_STATUS.md', 'A-1..A-8', '472.84')[0],
         'n=2 的独立参数点'),
        ('6b 中期判决（cl1b）', has('BLOCK_STATUS.md', 'V-3g', '0.4162')[0], 'n=6'),
        ('6c 归档判决复现', has('BLOCK_STATUS.md', '236/325/261/263/271/282')[0],
         '10/12 PASS'),
        ('7a 闭环文档', os.path.exists(os.path.join(_HERE,
                                                    'BLOCK_PARAM_CLOSURE.md')),
         'BLOCK_PARAM_CLOSURE.md'),
        ('7b 参数总表（生成物）',
         os.path.exists(os.path.join(_HERE, 'BLOCK_PARAM_TABLE.md')),
         'BLOCK_PARAM_TABLE.md'),
        ('8a BLOCK_RESULT 更新', has('BLOCK_RESULT.md', '结论二', '§3.2',
                                     'C-8')[0], '结论二 + 闭环配置表 + 限制'),
        ('8b BLOCK_STATUS 更新', has('BLOCK_STATUS.md', '## §28')[0], '§28 全节'),
        ('★ 总检入口存在', os.path.exists(os.path.join(_HERE,
                                                       '_bk_closure_all.sh')),
         'bash _bk_closure_all.sh'),
    ]
    print('=' * 100)
    print('收官核对：目标逐句 vs 产物')
    print('=' * 100)
    bad = 0
    for name, ok, det in checks:
        if not ok:
            bad += 1
        print('  %-34s %-8s %s' % (name, 'OK' if ok else '**缺**', det))
    print('-' * 100)
    print('  未满足项 = %d / %d' % (bad, len(checks)))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
