#!/bin/bash
# _t5_git_s231.sh --- ★★★★★★ 找到并修好框架里阻挡"伸长机制"的真 BUG
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_fix_ellipse.py pipeline/ca_pf_framework/_t5_relaunch_mob.sh \
        pipeline/ca_pf_framework/_t5_amtrace.sh pipeline/ca_pf_framework/_t5_amfail.sh \
        pipeline/ca_pf_framework/_t5_mobprog.sh pipeline/ca_pf_framework/_t5_waitam.sh \
        pipeline/ca_pf_framework/windowB_surface.py 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s231 ★★★★★★ 找到并修好框架里阻挡"伸长机制"的真 BUG（ellipse 分支从未跑过）

## 用户目标
"起这个验证，验证一下当前的物理公式是否真正起作用，如果起作用，就将其和已经证明有效的
--eng-elong 叠加在一起试一下"

## 结果：**公式目前**根本跑不起来** —— 因为它有一个真 BUG（我已修）
起两臂(t5AM_ell: --mob-iform ellipse; t5AM_combo: + --eng-elong 7) =>
**两臂都在 step 0 以 exit=1 退出**(墙钟 159.7 s / 156.6 s)。

## 确切 traceback
```
windowB_surface.py:4678  (在 `mob_iform == 'ellipse'` 分支内)
  _nh2 = (np.asarray(sorted(npref.values())[0], float).ravel() ...
ValueError: The truth value of an array with more than one element is ambiguous.
```
根因: `npref` 的**值是三维法向矢量(numpy 数组)**, 而 `sorted()` 用 `<` 逐对比较
=> 长度>1 的数组比较返回**布尔数组** => ValueError。
=> **这个分支从来没有被成功跑过**(一进入就崩) —— 与仓库自己记的
   "P1-31 实测: 解析各向异性 9.90、**引擎实际 1.24**" 相印证(那个数大概来自别处或早期版本)。

## 修法(最小、保持作者意图)
同一段下一行是 `_wv2 = np.asarray(_wt2[1], float).ravel()` => 作者意图是"取某一个变体的轴"
=> 改为**按键**排序取第一个键(`sorted(npref.keys())[0]`), 不再对数组做比较。语义不变。
安全性: 本段被 `mob_iform == 'ellipse'` 闸住(默认 'exp2') => **默认路径不进入
=> 对所有已跑/在跑的臂逐位不变**。
自验证补丁: 备份 -> 内存改 -> compile 通过才写盘 -> 复核; 并**核实非注释行里旧代码已消失**
(第一次复核报"残留 1 次", 查出是**我自己注释里引用了旧代码**, 不是真残留)。

## 验证(决定性判据)
归档崩溃目录(mv 改名, 绝不删除)后重启两臂 =>
 **Traceback 次数 = 0**(之前 1) · **已跑过 step 1 并成功形核**("athermal 形核 @ step 1:
 T=849.0 K = T_1 理论值", df=1.2273e+08, 场 2/场 3) => **引擎正常运转** ✓
(series.csv 显示 0 是因为它只在 --every 20 的行才写, step 20 才出第一行)

## 所以对用户问题的回答(阶段一)
**"当前物理公式是否真正起作用" => 之前**完全没起作用**(一开就崩); 现已修好并可运行,
但**"它给出的各向异性到底是多少"仍待测**(这正是 2x2 要做的事)。
MSGEOF
git log --oneline -1
