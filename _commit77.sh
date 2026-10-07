#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
cat _sec77.md >> IMPLEMENTATION_PLAN.md
cd /mnt/f/speed_up || exit 1
rm -f .git/index.lock
git add pipeline/ca_pf_framework/IMPLEMENTATION_PLAN.md pipeline/ca_pf_framework/_sec77.md
git commit -q -F - <<'EOF'
IMPLEMENTATION_PLAN 7.7: NEEDS USER ADJUDICATION -- who is the "solute" in the model?

Tm=1941 K, k=0.6303, c0=0.036, T_int=1911.1 K are mutually consistent ONLY under
"solute depresses the liquidus and is rejected by the solid" (k smaller than 1):
van 't Hoff m_L = 818.4 K gives T_liq(0.036) = 1911.54 K vs input 1911.1 K (0.4 K).
But V is the opposite: Tm(V)=2183 K, so V RAISES the Ti liquidus (m_L negative) and
is enriched in beta (k_V greater than 1) => T_liq(0.036) = 1958 K, not 1911.1 K.
Three readings: (A) the solute is Al and c0 is mis-assigned (0.102 vs 0.036);
(B) the solute is V and both the k sign and the T usage are wrong; (C) a quasi-binary
whose calibration case must be named. Does NOT block option (a)'s structural
verification, which only needs SOME free energy that admits a common tangent.
EOF
git log --oneline -1