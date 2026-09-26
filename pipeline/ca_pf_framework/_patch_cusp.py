# -*- coding: utf-8 -*-
"""P3 补丁：**尖点（近奇异）界面能** 的 Herring 刚度（cusp / faceted）。
   gamma(th) = gamma0 * (1 + Lam * sqrt(sin^2 th + eps^2))
   -> gamma + gamma_tt = gamma0*(1+Lam*s) + gamma0*Lam*(eps^2 - s^4 - 2 s^2 eps^2)/s^3
      其中 s = sqrt(sin^2 th + eps^2)。
   性质（关键）：**处处凸**（theta=90 处 gamma_tt = -gamma0*Lam，
   而 gamma = gamma0(1+Lam) => gamma+gamma_tt = gamma0 > 0 ✓；theta->0 处 gamma_tt -> +inf）
   => **无需 Wulff 凸化**，且惯习面处刚度极大 => 惯习面成为**刚性平面**（抗 Gibbs-Thomson 拉圆）。
   幂等。"""
import io
P = 'windowB_surface.py'
s = io.open(P, encoding='utf-8').read()
orig = s

anchor = "def herring_stiffness(ndot2, gamma0, Lam, herring=True):"
ins = '''def herring_stiffness_cusp(ndot2, gamma0, Lam, eps_c=0.05):
    """**尖点/近奇异**界面能的 Herring 刚度 gamma + gamma_tt。

        gamma(th)  = gamma0 * (1 + Lam * sqrt(sin^2 th + eps_c^2))
        gamma_tt   = gamma0 * Lam * (eps_c^2 - s^4 - 2 s^2 eps_c^2) / s^3,   s^2 = sin^2 th + eps_c^2

    ★ 为什么需要它（本轮实测 D11/长时程给的定量理由）：
      孤立单核长跑（beta_h=3.5, beta_w=2.3）：300 步 aspect 3.49 -> 1200 步 **2.23**，
      而**法向厚度反而长了 2.4x**。=> 形状弛豫（Gibbs-Thomson，驱动力 = gamma*kappa）
      用**各向同性的 gamma** 把薄饼**拉圆**了 => 光有 M(n) 钉扎**维持不住**板条。
      要维持，必须让惯习面同时是**低能面 + 刚性面**。

    ★ 凸性（已逐项核对，故**不需要** Wulff 凸化）：
        th -> 90 deg: gamma_tt -> -gamma0*Lam, gamma -> gamma0(1+Lam)
                      => gamma+gamma_tt -> gamma0 > 0  ✓
        th -> 0     : s -> eps_c => gamma_tt -> +gamma0*Lam/eps_c  (>0, 发散) ✓
      => 处处凸；且惯习面处刚度 ~ gamma0*Lam/eps_c **极大** => 该面极稳定。
    Lam 的物理：gamma(惯习面)/gamma(无序面) = 1/(1+Lam)。取 Lam=0.4 => 比 0.71。
    """
    s2 = np.clip(1.0 - ndot2, 0.0, 1.0)
    s2e = s2 + eps_c ** 2
    s = np.sqrt(s2e)
    g = gamma0 * (1.0 + Lam * s)
    gtt = gamma0 * Lam * (eps_c ** 2 - s2 ** 2 - 2.0 * s2 * eps_c ** 2) / (s2e ** 1.5)
    return g + gtt


def herring_stiffness(ndot2, gamma0, Lam, herring=True):'''
assert anchor in s
if 'herring_stiffness_cusp' not in s:
    s = s.replace(anchor, ins, 1)

# advance 签名加 facet_lam / facet_eps
s = s.replace("mob_aniso=0.0, pin_min=True, mob_beta=0.0, mob_beta_w=0.0):",
              "mob_aniso=0.0, pin_min=True, mob_beta=0.0, mob_beta_w=0.0,\n"
              "                facet_lam=0.0, facet_eps=0.05):", 1)

# 在 stiff 计算处：facet 优先
old = ("            if aniso > 0 and npref is not None and npref.get(k) is not None:\n")
new = ("            if facet_lam > 0.0 and npref is not None and npref.get(k) is not None:\n"
       "                # ★ P3：尖点界面能（只在给了 npref 的场上用）\n"
       "                n = np.stack([gi / gn[k] for gi in g], -1)\n"
       "                nd = np.asarray(npref[k], float)\n"
       "                nd = nd / (np.linalg.norm(nd) + 1e-300)\n"
       "                c2f = np.clip((n @ nd) ** 2, 0.0, 1.0)\n"
       "                gk = herring_stiffness_cusp(c2f, gk, facet_lam, facet_eps)\n"
       "            if aniso > 0 and npref is not None and npref.get(k) is not None:\n")
assert old in s
if 'facet_lam > 0.0' not in s:
    s = s.replace(old, new, 1)

if s != orig:
    io.open(P, 'w', encoding='utf-8').write(s)
    print('patched: cusp gamma')
else:
    print('nothing')
