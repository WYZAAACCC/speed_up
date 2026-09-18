# 源码索引与审计定位

| 路径 | 作用 | 关注点 |
|---|---|---|
| `pipeline/stage1_meltpool_c.i` | 生产源输入 | 网格、温度、8 序参量、CH、Landau、求解器 |
| `pipeline/stage1_meltpool_d.i` | 生成后实际输入 | 检查生成器是否漂移 |
| `pipeline/frozen/gen_aniso_nonad.py` | 非 AD 各向异性生成器 | 取向差、热梯度对齐、材料导数 |
| `pipeline/frozen/splice_aniso_nonad.py` | 拼接器 | 生产核和耦合变量 |
| `pipeline/run_nonad_prod.sh` | 生产守卫与运行 | hash、参数断言、输出 |
| `pipeline/tests/front1d.i` | 1D 前沿 | 分配、截留、守恒 |
| `pipeline/tests/make_front1d.py` | 前沿扫描生成器 | `W/(D/V)` 扫描、dx 设置 |
| `pipeline/tests/grain_growth_circle.i` | 圆晶粒长大 | `R²` 收敛 |
| `pipeline/tests/verify_f_grain.i` | Landau 自由能梯度 | ④ 结构验证 |
| `pipeline/tests/make_partition_sweep.py` | 分配系数扫描 | `kappa_c` 依赖 |
| `pipeline/extract.py` | Exodus 到逐面数据 | 多块网格、面标签、守恒 |
| `pipeline/train_operator_v3.py` | 逐面 NN | 守恒聚合和时间切分 |
| `pipeline/OPEN_PROBLEMS.md` | 未决问题 | 不能当作已解决事实 |
| `pipeline/GB_SOLUTE_GOAL.md` | 晶界溶质目标 | 偏析、扩散、拖曳的目标定义 |
| `pipeline/GATE1_PLAN.md` | Gate 1 计划 | 1D 扫描和止损线 |

## 推荐代码检查命令

```bash
rg -n "coupled_parsed|coupled_variables|kappa_c|prop_values|f_loc|f_grain|T_mid|dT|M|Adaptivity|Antitrapping" pipeline
python3 -m py_compile pipeline/*.py pipeline/frozen/*.py pipeline/tests/*.py
(cd pipeline/frozen && sha256sum -c SHA256SUMS)
```

## 外部理论参考

- [Plapp 2011, grand-potential phase-field model](https://arxiv.org/abs/1105.1670)
- [Echebarria et al. 2004, quantitative alloy phase field and antitrapping](https://arxiv.org/abs/cond-mat/0404164)
- [MOOSE Adaptivity](https://mooseframework.inl.gov/syntax/Adaptivity/)
- [MOOSE Jacobian guidance](https://mooseframework.inl.gov/application_development/jacobian_definition.html)
