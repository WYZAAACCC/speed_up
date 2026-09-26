#include "ScaledCoupledTimeDerivative.h"

registerMooseObject("GibbsApp", ScaledCoupledTimeDerivative);

InputParameters
ScaledCoupledTimeDerivative::validParams()
{
  InputParameters params = CoupledTimeDerivative::validParams();
  params.addClassDescription(
      "Residual = scale * dv/dt * test, where scale is a material property. "
      "用于 Gibbs 面模型的局域平衡表述：(1 + shape*As) * dc/dt + div(M grad w) = 0");
  params.addRequiredParam<MaterialPropertyName>("scale", "乘在 dv/dt 上的材料系数");
  params.addCoupledVar("args", "scale 依赖的**非线性**变量（用于补齐非对角雅可比）");
  return params;
}

ScaledCoupledTimeDerivative::ScaledCoupledTimeDerivative(const InputParameters & parameters)
  : DerivativeMaterialInterface<JvarMapKernelInterface<CoupledTimeDerivative>>(parameters),
    _scale(getMaterialProperty<Real>("scale")),
    _dscale_du(getMaterialPropertyDerivative<Real>("scale", _var.name())),
    _dscale_dv(getMaterialPropertyDerivative<Real>("scale", coupledName("v"))),
    _n_args(coupledComponents("args")),
    _dscale_darg(_n_args)
{
  // 照抄 MatReaction 的写法（框架里已在用、已验证）
  for (unsigned int i = 0; i < _n_args; ++i)
    _dscale_darg[i] = &getMaterialPropertyDerivative<Real>("scale", i);
}

void
ScaledCoupledTimeDerivative::initialSetup()
{
  validateNonlinearCoupling<Real>("scale");
}

Real
ScaledCoupledTimeDerivative::computeQpResidual()
{
  return _scale[_qp] * CoupledTimeDerivative::computeQpResidual();
}

Real
ScaledCoupledTimeDerivative::computeQpJacobian()
{
  // 对角：只有 scale 依赖本变量 u 的那部分（v 的导数走非对角）
  return _dscale_du[_qp] * _v_dot[_qp] * _phi[_j][_qp] * _test[_i][_qp];
}

Real
ScaledCoupledTimeDerivative::computeQpOffDiagJacobian(unsigned int jvar)
{
  // 对 v 的导数：scale * d(v_dot)/d(v) * test
  if (jvar == _v_var)
    return _scale[_qp] * _dv_dot[_qp] * _phi[_j][_qp] * _test[_i][_qp];

  // 其余：d(scale)/d(args) * v_dot * test
  const auto cvar = mapJvarToCvar(jvar);
  return (*_dscale_darg[cvar])[_qp] * _v_dot[_qp] * _phi[_j][_qp] * _test[_i][_qp];
}