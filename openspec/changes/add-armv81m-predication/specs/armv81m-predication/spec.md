## ADDED Requirements
### Requirement: Parse new predication instructions
The system SHALL parse Armv8.1-M predication/control instructions in `arch_v81m.py`:
- `vmsr <Pp>, <Rn>` and `vmrs <Rd>, <Pp>`
- `VPST{x{y{z}}}` (mask-only seed that uses current `P0`)
- `VPT{x{y{z}}}.<dt> <fc>, Qn, Rm` and `VPT{x{y{z}}}.<dt> <fc>, Qn, Qm` (seed that computes `P0` and starts a block)
- `vpsel Qd, Qn, Qm`

#### Scenario: Parse VMSR/VMRS
- WHEN source contains `vmsr p0, r3` and `vmrs r1, p0`
- THEN both lines parse as valid instructions with `p0` typed as `PRED` and `r1/r3` as `GPR`

#### Scenario: Parse VPST with mask
- WHEN source contains `vpstt` or `vpstee`
- THEN it parses as a predication seed using the current `VPR.P0`; the block length is 1 + len(mask) (2 or 3 here). The first consumer is implicitly `t`; subsequent consumers must be `t`/`e` as specified by the mask. VPST does not compute or modify `P0`.

#### Scenario: Parse VPT seed and mask (vector vs scalar compare)
- WHEN source contains `vptte.u32 ge, q0, r1` and `vptt.s16 lt, q2, q3`
- THEN each parses as a predication seed that computes `VPR.P0` by lane-wise comparison of `Qn` with `Rm` or `Qm` using the `<dt>` type and `<fc>` condition; the block length is 1 + len(mask) (here 3 and 2). The first consumer is implicitly `t`; subsequent consumers must be `t`, `e` according to the mask.

#### Scenario: Parse VPSEL
- WHEN source contains `vpsel q0, q1, q2`
- THEN it parses as a vector select reading `P0` without creating or consuming VPT/VPST slots

### Requirement: Recognize predicated mnemonics (…t/…e)
All predicable MVE operations SHALL accept predicated mnemonic variants ending in `t` (then) or `e` (else), e.g., `vaddt.u32`, `vadde.s16`.

#### Scenario: Parse predicated variant
- WHEN source contains `vaddt.u32 q0, q1, q2`
- THEN it parses as `vadd.u32` with attributes `predicated=True` and `predicate_kind='t'`

### Requirement: Successive predicate-slot consumption
After a VPT/VPST seed, the block MUST comprise the next N predicated MVE instructions (1 ≤ N ≤ 4) immediately following the seed; each predicated instruction MUST consume one slot in order.
- For VPST: consumers use the current `P0` (`t` uses `P0`, `e` uses `!P0`).
- For VPT: consumers must match `t + mask`; `t` lanes use the comparison result, `e` lanes use its inverse.

#### Scenario: VPT with mixed T/E
- WHEN code is:
  - `vpt ge, q0, r0`
  - `vaddt.u32 q0, q1, q2`
  - `vsube.u32 q3, q4, q5`
- THEN the predicated kinds must use the computed `P0` for `t` and its inverse for `e`; each consumes successive slots; no other instruction may appear between them

### Requirement: Adjacency (reordering) constraint
All predicated instructions in a VPT/VPST block MUST immediately follow the seed instruction in program order; the scheduler SHALL NOT move unrelated instructions into or out of the block.

#### Scenario: Adjacency enforced
- WHEN the optimizer considers reordering
- THEN it MUST keep the seed and its N predicated consumers as a contiguous block with no gaps

### Requirement: VPSEL exception
`vpsel` SHALL read `P0` contents but SHALL NOT consume or require VPT/VPST slots. It is not bound by the adjacency rule.

#### Scenario: VPSEL outside VPT/VPST
- WHEN code contains `vpsel q0, q1, q2` without a nearby `vpt/vpst`
- THEN parsing and scheduling remain valid; no slot consumption occurs

### Requirement: Tests
`tests/naive/armv8m/instructions.s` SHALL include the new instructions and sample predicated forms.

#### Scenario: Instruction presence
- WHEN running parser tests
- THEN the added lines for `vmsr/vmrs/vpst/vpt/vpsel` and a few `…t/…e` variants parse successfully
