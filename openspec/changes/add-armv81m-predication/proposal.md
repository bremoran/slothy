# Change: Add Armv8.1-M predication support (VPT/VPST/VMSR/VMRS/VPSEL)

## Why
Armv8.1-M (Helium/MVE) predication is not modeled: the parser lacks VPT/VPST/VMSR/VMRS/VPSEL, predicated mnemonics (…t/…e) are not recognized, and no constraint enforces adjacency of predicated instructions to their VPT/VPST seed. This limits correctness and blocks algorithms that rely on predication.

## What Changes
- Parse new instructions: `vmsr`, `vmrs`, `VPST{x{y{z}}}`, `VPT{x{y{z}}}.<dt> <fc>, Qn, Rm` and `VPT{x{y{z}}}.<dt> <fc>, Qn, Qm`, `vpsel`.
- Accept predicated mnemonic variants (`…t`/`…e`) for MVE ops.
- Model successive predication-block consumption (up to 4):
  - VPT: computes `VPR.P0` by comparing `Qn` with `Rm` or `Qm` using lane type `<dt>` and condition `<fc>`, and starts a block whose mask (`x{y{z}}`) encodes T/E for consumers 2–4; the first consumer is implicitly `t`.
  - VPST: starts a block whose consumers use the current `VPR.P0`; mask (`x{y{z}}`) encodes T/E for consumers 2–4. VPST does not compute or modify `P0`.
- Reordering constraint: all predicated instructions in a VPT/VPST block immediately follow the seed in program order.
- Exception: `vpsel` reads `P0` but does not consume VPT/VPST slots, and is not adjacency‑bound.
- Tests: extend `tests/naive/armv8m/instructions.s` with examples for these ops and predicated forms.

## Impact
- Affected specs: `armv81m-predication`.
- Affected code: `slothy/targets/arm_v81m/arch_v81m.py`, `slothy/targets/arm_v81m/cortex_m55r1.py`, `tests/naive/armv8m/instructions.s`.
