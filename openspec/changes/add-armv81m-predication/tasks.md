## 1. Implementation
- [x] 1.1 Parser: add classes for `vmsr`, `vmrs`, `VPST{x{y{z}}}`, `VPT{x{y{z}}}.<dt> <fc>, Qn, Rm` and `VPT{x{y{z}}}.<dt> <fc>, Qn, Qm`, `vpsel` in `arch_v81m.py`
- [x] 1.2 Predicated mnemonics: normalize `…t`/`…e` in `MVEInstruction.build()`; store `predicated={true,false}`, `predicate_kind={t,e,None}`
- [x] 1.3 Predication block state: add a predication seed object for VPT/VPST (mask, cond/src, block_len, block_id); VPT computes `P0` from `<dt> <fc>, Qn, Rm|Qm`; VPST uses current `P0`; assign `pred_slot_index` in order and validate `t + mask`
- [x] 1.4 Constraints: expose `add_predication_constraints(slothy)` in `arch_v81m.py`; enforce adjacency and slot counting; call from `cortex_m55r1.add_further_constraints`
- [x] 1.5 ExecUnits & latency: map `vmsr/vmrs/vpt/vpst`→SCALAR, `vpsel`→VEC_INT; default latency 1 unless data shows otherwise
- [x] 1.6 Tests: extend `tests/naive/armv8m/instructions.s` with examples; add a minimal DFG-based test later to assert adjacency (optional in follow-up)

## 2. Validation
- [x] 2.1 Parse-only: `pytest -k armv8m` parses new lines without errors
- [x] 2.2 Reordering on: with `allow_reordering=True`, verify VPT/VPST blocks remain adjacent
- [x] 2.3 Exception path: `vpsel` allowed anywhere; no slot decrement
- [ ] 2.4 Back-compat: existing tests pass

## 3. Docs
- [x] 3.1 Brief note in README (Armv8.1-M target) describing predication rules, VPT vs VPST prototypes, and the VPSEL exception
