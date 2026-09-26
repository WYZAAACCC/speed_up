// =============================================================================
// ConstAdvection —— 残差 = v · ∇u · test（v 来自 RealVectorValue 材料）
// =============================================================================
// 用途：Gibbs 面的"动态"——在**晶界参考系**里，材料以速度 v 流过晶界，
// 等价于晶界在材料里以 v 迁移。体相溶质方程多一项 v·∇c。
//
// 为什么要自己写：
//   `ConservativeAdvection` 的 `velocity` 参数要的是**向量耦合变量**（实测报
//   "coupled variable 'vel' was not found"），而 `MatAdvection` 不在 framework 里。
//   对**常速度场**，div(v*c) = v·grad(c)，所以这个非守恒形式的残差与守恒形式等价。
// =============================================================================
#pragma once

#include "Kernel.h"

class ConstAdvection : public Kernel
{
public:
  static InputParameters validParams();

  ConstAdvection(const InputParameters & parameters);

protected:
  virtual Real computeQpResidual() override;
  virtual Real computeQpJacobian() override;

  /// 速度（RealVectorValue 材料，例如 GenericConstantRealVectorValue）
  const MaterialProperty<RealVectorValue> & _vel;
};