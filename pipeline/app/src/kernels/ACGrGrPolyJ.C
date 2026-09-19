//* 自建 MOOSE 核：ACGrGrPoly 的雅可比补全版 —— 实现
#include "ACGrGrPolyJ.h"

registerMooseObject("GbJacApp", ACGrGrPolyJ);

InputParameters
ACGrGrPolyJ::validParams()
{
  InputParameters params = ACGrGrPoly::validParams();
  params.addClassDescription(
      "ACGrGrPoly 的雅可比补全版：残差与 ACGrGrPoly 逐位相同，"
      "补回它丢掉的 dL/deta_j 与 d(gamma_asymm)/deta_j 两项");
  params.addParam<MaterialPropertyName>(
      "gamma_name", "gamma_asymm", "各向异性交叉项系数的材料属性名");
  params.addParam<MooseEnum>("jac_mode",
                             MooseEnum("full off zero_all", "full"),
                             "雅可比采样模式。`full`=生产用的完整补全；"
                             "`off`=丢掉全部非对角项；`zero_all`=**连对角贡献也归零**。"
                             "仅供 T1 判据的正对照使用 —— 三者残差逐位相同。");
  return params;
}

ACGrGrPolyJ::ACGrGrPolyJ(const InputParameters & parameters)
  : ACGrGrPoly(parameters),
    _gamma_name(getParam<MaterialPropertyName>("gamma_name")),
    _dgamma_dop(getMaterialPropertyDerivative<Real>(_gamma_name, _var.name())),
    _dgamma_dv(_op_num),
    _jac_mode(getParam<MooseEnum>("jac_mode"))
{
  // 按 `v` 的**名字**逐个取导数，而不是按 `coupled_variables` 的下标：
  // coupled_variables 里有 T，而 gamma_asymm 不依赖 T，
  // 若按 coupled_variables 取 d(gamma)/dT 会直接报"该导数不存在"。
  const std::vector<VariableName> & vnames = getParam<std::vector<VariableName>>("v");
  for (unsigned int i = 0; i < _op_num; ++i)
    _dgamma_dv[i] = &getMaterialPropertyDerivative<Real>(_gamma_name, vnames[i]);
}

Real
ACGrGrPolyJ::computeDFDOP(PFFunctionType type)
{
  Real val = ACGrGrPoly::computeDFDOP(type);

  if (type == Jacobian && _jac_mode == "full")
  {
    const Real op = assignThisOp();
    const std::vector<Real> other_ops = assignOtherOps();

    Real SumOPj = 0.0;
    for (unsigned int i = 0; i < _op_num; ++i)
      SumOPj += other_ops[i] * other_ops[i];

    // ∂/∂η_self [ 2·mu·γ(η)·η·Σ ] 里经由 γ 的那一半。
    // 另一半（显式的 η_self）基类已经算了。
    val += _mu[_qp] * 2.0 * _dgamma_dop[_qp] * _phi[_j][_qp] * op * SumOPj;
  }

  return val;
}

Real
ACGrGrPolyJ::computeQpOffDiagJacobian(unsigned int jvar)
{
  // 正对照：整个 η–η 非对角块归零。残差不受影响（computeQpResidual 未被触碰）。
  // ⚠ 实测这个删除在 Frobenius 范数下几乎为零（`||J||` 只变 −0.003%）——
  //   因为这些项是 η_i·η_j 型的，**只在晶界单元上非零**。
  //   ⇒ 要真正的量级级对照，用 `jac_mode = zero_all`。
  if (_jac_mode == "off" || _jac_mode == "zero_all")
    return 0.0;

  // (1) 基类：Σ 里显式 η_j 的那一项（jvar 属于 v 时才有意义，否则基类返回 0）
  Real jac = ACGrGrPoly::computeQpOffDiagJacobian(jvar);

  const Real op = assignThisOp();
  const std::vector<Real> other_ops = assignOtherOps();

  Real SumOPj = 0.0;
  for (unsigned int i = 0; i < _op_num; ++i)
    SumOPj += other_ops[i] * other_ops[i];

  // (2) γ 的各向异性项：L·mu·2·(∂γ/∂η_j)·η_i·Σ
  for (unsigned int i = 0; i < _op_num; ++i)
    if (jvar == _vals_var[i])
      jac += _L[_qp] * _mu[_qp] * 2.0 * (*_dgamma_dv[i])[_qp] * _phi[_j][_qp] * op * SumOPj *
             _test[_i][_qp];

  // (3) 迁移率乘积法则项 —— ACGrGrPoly 覆盖 ACBulk::computeQpOffDiagJacobian 时丢掉的。
  //     直接复用 ACBulk 的实现，与 AllenCahn.C:65 同一写法。
  //
  //     安全性：走到这里 jvar 一定在 `coupled_variables` 里 ——
  //     框架的 JvarMapKernelInterface::computeOffDiagJacobian 已经在
  //     `_jvar_map[jvar] < 0` 时提前返回（JvarMapInterface.h:204），
  //     所以 ACBulk 里 `mapJvarToCvar(jvar)` 拿到的下标一定有效。
  //
  //     ⚠ 不要改用 `bool mapJvarToCvar(jvar, cvar)` 那个重载：
  //     libmoose 只实例化了对 KernelValue 的 `unsigned int` 版本，
  //     bool 版在链接期报 "undefined symbol:
  //     JvarMapInterfaceBase<KernelValue>::mapJvarToCvar(unsigned int, unsigned int&)"。
  //     （实测踩过。）
  jac += ACBulk<Real>::computeQpOffDiagJacobian(jvar);

  return jac;
}

Real
ACGrGrPolyJ::precomputeQpJacobian()
{
  // 正对照的**量级级**版本：本核的对角贡献在每个单元上都非零，
  // 删掉它是真正的「删掉一个大项」。
  //
  // ⚠ 必须是 `precomputeQpJacobian` 而非 `computeQpJacobian` ——
  //   见头文件里的说明（KernelValue 走的是前者）。
  if (_jac_mode == "zero_all")
    return 0.0;

  return ACGrGrPoly::precomputeQpJacobian();
}
