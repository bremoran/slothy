#!/usr/bin/env python3
# import slothy
import logging
from slothy import Slothy, Config
import sys


import slothy.targets.arm_v81m.arch_v81m as Arch_Armv81M
import slothy.targets.arm_v81m.cortex_m55r1 as Target_CortexM55r1
import slothy.targets.arm_v81m.cortex_m85r1 as Target_CortexM85r1

target_label_dict = {Target_CortexM55r1: "m55",
                     Target_CortexM85r1: "m85"}

arch = Arch_Armv81M
target = Target_CortexM55r1

handlers = []
h_err = logging.StreamHandler(sys.stderr)
h_err.setLevel(logging.WARNING)
handlers.append(h_err)
h_verbose = logging.StreamHandler(sys.stdout)
h_verbose.setLevel(logging.DEBUG)
h_verbose.addFilter(lambda r: r.levelno < logging.INFO)
handlers.append(h_verbose)
logging.basicConfig(
    level=logging.DEBUG,
    handlers=handlers,
)

slothy = Slothy(arch, target, logger = logging.getLogger("gen_keccak"))

x_names = 'aeiou'
y_names = 'bgkms'


def sym_vxy(sym: str, x:list[int], y:int):
    return f'q<{sym}{y_names[y]}{''.join([x_names[xi] for xi in x])}>'
def sym_xvy(sym: str, x:int, y:list[int]):
    return f'q<{sym}{''.join([y_names[yi] for yi in y])}{x_names[x]}>'
def sym_vxvy(sym, x:list[int], y:list[int]):
    return f'{sym}{''.join([y_names[yi] for yi in y])}{''.join([x_names[xi] for xi in x])}'
def sym_xy(sym: str, x:int, y:int):
    return f'r<{sym}{y_names[y]}{x_names[x]}>'
def sym_vx(sym: str, x:int):
    return f'q<{sym}{''.join([x_names[xi] for xi in x])}>'
def sym_x(sym: str, x:int):
    return f'r<{sym}{x_names[x]}>'

def sym(sym:str, x:int|list[int], y:int|list[int] = None):
    if isinstance(x, list) and isinstance(y, list):
        return sym_vxvy(sym, x, y)
    elif isinstance(x, list) and isinstance(y, int):
        return sym_vxy(sym, x, y)
    elif isinstance(x, list):
        return sym_vx(sym, x)
    elif isinstance(y, list):
        return sym_xvy(sym, x, y)
    elif isinstance(y, int):
        return sym_xy(sym, x, y)
    else:
        return sym_x(sym, x)

def n_mod_5(s: int, n: int):
    return list(((s+i)%5 for i in range(n)))
    
def mk_rt():
    rt = [[0]*5,[0]*5,[0]*5,[0]*5,[0]*5 ]
    xy = (1,0)
    for t in range(24):
            r = (((t+1) * (t+2))//2)%64
            x,y = xy
            rt[x][y] = r
            xy = (y * 1, (x * 2 + y * 3) % 5 )
    return rt

def should_rot32(rt,o,x,y):
    r = rt[x][y]
    if r%2:
        if o == 0:
            return ((r-1)//2)%32 != 0
        else:
            return ((r+1)//2)%32 != 0
    else:
        return (r//2)%32 != 0
    
def sym_AtoB_norot32(rt, o, x, y):
    sym_A = sym(f'A{o}', x, y)
    r = rt[x][y]
    sym_B = sym(f'B{1-o if r%2 else o}', y, (2*x + 3*y) % 5)
    return sym_A if should_rot32(rt, o, x, y) else sym_B

def gen_keccak():
    rot = mk_rt()
    # s += (rot) + '\n'
    s = f'''
.thumb
.syntax unified
.text
BOffsets: .byte {', '.join([f'{20*x}' for x in range(4)])}
@----------------------------------------------------------------------------
@
@ void KeccakF1600_StatePermute_hybrid( void *state )
@
.align 8
.global   KeccakF1600_StatePermute_hybrid
.type KeccakF1600_StatePermute_hybrid,%function
KeccakF1600_StatePermute_hybrid:
	push	{{ r4 - r12, lr }}
    mov lr, 24
    wls lr, lr, roundend
roundstart:
'''

    # Round[b](A,RC) {
    # θ step
    # C[x] = A[x,0] xor A[x,1] xor A[x,2] xor A[x,3] xor A[x,4],   for x in 0…4
    n14 = n_mod_5(1, 4)
    for y in range(5):
        A0xy = sym_vxy("A0", n14, y)
        s += (f'    vldrw.u32 {A0xy}, [r0, #{y*20+4}]') + '\n'
    C0v = sym('C0', n14)
    s += (f'    veor {C0v}, {sym_vxy("A0", n14, 0)}, {sym_vxy("A0", n14, 1)}') + '\n'
    s += (f'    veor {C0v}, {C0v}, {sym_vxy("A0", n14, 2)}') + '\n'
    s += (f'    veor {C0v}, {C0v}, {sym_vxy("A0", n14, 3)}') + '\n'
    s += (f'    veor {C0v}, {C0v}, {sym_vxy("A0", n14, 4)}') + '\n'

    for y in range(5):
        A1xy = sym_vxy("A1", n14, y)
        s += (f'    vldrw.u32 {A1xy}, [r0, #{y*20+4+100}]') + '\n'
    C1v = sym('C1', n14)
    s += (f'    veor {C1v}, {sym_vxy("A1", n14, 0)}, {sym_vxy("A1", n14, 1)}') + '\n'
    s += (f'    veor {C1v}, {C1v}, {sym_vxy("A1", n14, 2)}') + '\n'
    s += (f'    veor {C1v}, {C1v}, {sym_vxy("A1", n14, 3)}') + '\n'
    s += (f'    veor {C1v}, {C1v}, {sym_vxy("A1", n14, 4)}') + '\n'

    # Now do the same for column 0
    for o in range(2):
        C = sym(f'C{o}', 0)
        for y in range(1,5):
            Axy = sym(f"A{o}", 0, y)
            s += (f'    ldr {Axy}, [r0, #{20*y + o*100}]') + '\n'
        s += (f'    eor {C}, {sym(f"A{o}", 0, 0)}, {sym(f"A{o}", 0, 1)}') + '\n'
        s += (f'    eor {C}, {C}, {sym(f"A{o}", 0, 2)}') + '\n'
        s += (f'    eor {C}, {C}, {sym(f"A{o}", 0, 3)}') + '\n'
        s += (f'    eor {C}, {C}, {sym(f"A{o}", 0, 4)}') + '\n'

    # D[x] = C[x-1] xor rot(C[x+1],1),                             for x in 0…4
    # Need to compose C42
    for o in range(2):
        C = sym(f'C{o}', n_mod_5(1,4))
        # Extract C1,2,3,4
        s += (f'    vmov {sym(f"C{o}", 1)}, {sym(f"C{o}", 3)}, {C}[2], {C}[0]') + '\n'
        s += (f'    vmov {sym(f"C{o}", 2)}, {sym(f"C{o}", 4)}, {C}[3], {C}[1]') + '\n'
        C42 = sym(f'C{o}', n_mod_5(4,4))
        s += (f'    vmov {C42}[2], {C42}[0], {sym(f"C{o}", 4)}, {sym(f"C{o}", 1)}') + '\n'
        s += (f'    vmov {C42}[3], {C42}[1], {sym(f"C{o}", 0)}, {sym(f"C{o}", 2)}') + '\n'

    C0_42 = sym(f'C0', n_mod_5(4,4))
    C0_14 = sym(f'C0', n_mod_5(1,4))
    C1_42 = sym(f'C1', n_mod_5(4,4))
    C1_14 = sym(f'C1', n_mod_5(1,4))
    C1r1_14 = sym(f'C1r1', n_mod_5(1,4))
    s += (f'    vshl.u32  {C1r1_14}, {C1_14}, #1') + '\n'
    s += (f'    vsri.u32 {C1r1_14}, {C1_14}, #31') + '\n'
    D0_03 = sym("D0", n_mod_5(0, 4))
    D1_03 = sym("D1", n_mod_5(0, 4))
    s += (f'    veor {D0_03}, {C0_42}, {C1r1_14}') + '\n'
    s += (f'    veor {D1_03}, {C1_42}, {C0_14}') + '\n'

    C0_3 = sym("C0", 3)
    C0_0 = sym("C0", 0)
    C1_3 = sym("C1", 3)
    C1_0 = sym("C1", 0)
    C1_0r = sym("C1r", 0)
    D0_4 = sym("D0", 4)
    D1_4 = sym("D1", 4)

    # TODO: Replace with shifted version
    s += (f'    ror {C1_0r}, {C1_0}, #31') + '\n'
    s += (f'    eor {D0_4}, {C0_3}, {C1_0r}') + '\n'
    # s += (f'    eor {D0_4}, {C0_3}, {C1_0}, ROR #31') + '\n'
    s += (f'    eor {D1_4}, {C1_3}, {C0_0}') + '\n'

    # Rotate D so that it matches the A vectors already loaded.
    # vshlc will produce D[4:1], so we can't use that.
    # vmov would move elements in 4 instructions
    # Use 2x vmov & vrev64 to save one instruction
    for o in range(2):
        D03 = sym(f'D{o}', n_mod_5(0,4))
        D14 = sym(f'D{o}', n_mod_5(1,4))
        D0 = sym(f'D{o}', 0)
        D2 = sym(f'D{o}', 2)
        D4 = sym(f'D{o}', 4)
        s += (f'    vmov {D0}, {D2}, {D03}[2], {D03}[0]') + '\n'
        s += (f'    vrev64.32 {D14}, {D03}') + '\n'
        s += (f'    vmov {D14}[3], {D14}[1], {D2}, {D4}') + '\n'


    # A[x,y] = A[x,y] xor D[x],                           for (x,y) in (0…4,0…4)
    for o in range(2):
        vD = sym(f'D{o}', n_mod_5(1,4))
        rD = sym(f'D{o}', 0)
        for y in range(5):
            vA = sym(f'A{o}', n_mod_5(1,4), y)
            rA = sym(f'A{o}', 0, y)
            s += (f'    veor {vA}, {vD}, {vA}') + '\n'
            s += (f'    eor  {sym_AtoB_norot32(rot, o, 0, y)}, {rD}, {rA}') + '\n'
    
    # Scalar only
    # ρ and π steps
    # B[y,2*x+3*y] = rot(A[x,y], r[x,y]),                 for (x,y) in (0…4,0…4)
    for o in range(2):
        for y in range(5):
            vA = sym(f'A{o}', n_mod_5(1,4), y)
            rA = [sym_AtoB_norot32(rot, o, x, y) for x in range(5)]
            s += (f'    vmov {rA[1]}, {rA[3]}, {vA}[2], {vA}[0]') + '\n'
            s += (f'    vmov {rA[2]}, {rA[4]}, {vA}[3], {vA}[1]') + '\n'
    for x in range(5):
        for y in range(5):
            r = rot[x][y]
            A0 = sym("A0", x, y)
            A1 = sym("A1", x, y)
            B0 = sym("B0", y, (2*x+3*y)%5)
            B1 = sym("B1", y, (2*x+3*y)%5)
            if r%2:
                s += (f'   {'' if (r+1)//2 else ' //'} ror {B0}, {A1}, #32-{(r+1)//2}') + '\n'
                s += (f'   {'' if (r-1)//2 else ' //'} ror {B1}, {A0}, #32-{(r-1)//2}') + '\n'
            else:
                s += (f'   {'' if r//2 else ' //'} ror {B0}, {A0}, #32-{r//2}') + '\n'
                s += (f'   {'' if r//2 else ' //'} ror {B1}, {A1}, #32-{r//2}') + '\n'
    # χ step
    # Compose the transpose vectors
    for o in range(2):
        for x in range(5):
            vB = sym(f'B{o}', x, n_mod_5(1,4))
            s += (f'    vmov {vB}[2], {vB}[0], {sym(f'B{o}', x, 1)}, {sym(f'B{o}', x, 3)}') + '\n'
            s += (f'    vmov {vB}[3], {vB}[1], {sym(f'B{o}', x, 2)}, {sym(f'B{o}', x, 4)}') + '\n'
    # A[x,y] = B[x,y] xor ((not B[x+1,y]) and B[x+2,y]),  for (x,y) in (0…4,0…4)
    for o in range(2):
        for x in reversed(range(5)):
            vB0 = sym(f'B{o}', (x + 0) % 5, n_mod_5(1,4))
            vB1 = sym(f'B{o}', (x + 1) % 5, n_mod_5(1,4))
            vB2 = sym(f'B{o}', (x + 2) % 5, n_mod_5(1,4))
            vA = sym(f'A{o}', x, n_mod_5(1,4))
            s += (f'    vbic {vA}, {vB2}, {vB1}') + '\n'
            s += (f'    veor {vA}, {vA}, {vB0}') + '\n'
            rB0 = sym(f'B{o}', (x + 0) % 5, 0)
            rB1 = sym(f'B{o}', (x + 1) % 5, 0)
            rB2 = sym(f'B{o}', (x + 2) % 5, 0)
            rA = sym(f'A{o}', x, 0)
            s += (f'    bic {rA}, {rB2}, {rB1}') + '\n'
            s += (f'    eor {rA}, {rA}, {rB0}') + '\n'

    # Writeback
    # Vectors are in transpose form, so they need offset load/store
    s += (f'    mov       r<BOS>, #BOffsets') + '\n'
    s += (f'    vldrb.u32 q<BOR>, [r<BOS>]') + '\n'
    s += (f'    vadd.u32  q<BOR>, q<BOR>, r0') + '\n'
    for o in range(2):
        for x in range(5):
            vA = sym(f'A{o}', x, n_mod_5(1,4))
            s += (f'    vstrw.32 {vA}, [q<BOR>, #4]!') + '\n'
    for o in range(2):
        s += (f"    strd {sym(f'A{o}', 1, 0)}, {sym(f'A{o}', 2, 0)}, [r0, #{4+100*o}]") + '\n'
        s += (f"    strd {sym(f'A{o}', 3, 0)}, {sym(f'A{o}', 4, 0)}, [r0, #{12+100*o}]") + '\n'
    # ι step
    # A[0,0] = A[0,0] xor RC
    s += (f"    mov  r<RCAddr>, #RCTable") + '\n'
    #TODO: Replace with shifted version
    s += (f"    lsl  r<RCOff>, lr, #3") + '\n'
    s += (f"    add  r<RCAddr>, r<RCAddr>, r<RCOff>") + '\n'
    s += (f"    ldrd r<RC0>, r<RC1>, [r<RCAddr>]") + '\n'
    s += (f"    eor {sym('A0', 0, 0)}, {sym('A0', 0, 0)}, r<RC0>") + '\n'
    s += (f"    eor {sym('A1', 0, 0)}, {sym('A1', 0, 0)}, r<RC1>") + '\n'

    # return A
    # }
    s+=(f'''
    le lr, roundstart
roundend:
    vpop {{d8-d15}}
    ldmia.w sp!, {{r4,r5,r6,r7,r8,r9,r10,r11,r12, pc}}
''')
    return s

def main():
    instructions = gen_keccak()
    # for line in instructions:
    #     print(line)
    print(instructions)
    slothy.load_source_raw(instructions)
    # first pass: replace symbolic register names by architectural registers
    slothy.config.inputs_are_outputs=True
    slothy.config.outputs=["A0ba", "A1ba", "r0"]
    slothy.config.timeout = 60
    slothy.config.constraints.functional_only = True
    slothy.config.constraints.allow_reordering = False
    slothy.config.constraints.allow_spills = True
    slothy.config.constraints.minimize_spills = True
    slothy.optimize_loop(loop_lbl='roundstart')


    slothy.write_source_to_file("hybrid_keccak_arch-m55.s")
    print("done")
    # second pass: splitting heuristic
    slothy.config.timeout = 100
    slothy.config.constraints.functional_only = False
    slothy.config.constraints.allow_reordering = True
    slothy.config.constraints.allow_spills = False
    slothy.config.absorb_spills = False
    slothy.config.variable_size=True
    slothy.config.constraints.stalls_first_attempt=64
    slothy.config.constraints.stalls_maximum_attempt = 4096
    slothy.config.split_heuristic = True
    slothy.config.split_heuristic_stepsize = 0.05
    slothy.config.split_heuristic_factor = 10
    slothy.config.split_heuristic_repeat = 2
    slothy.config.split_heuristic_estimate_performance = False
    slothy.config.split_heuristic_optimize_seam = 2

    slothy.optimize_loop(loop_lbl='roundstart')
    slothy.write_source_to_file("hybrid_keccak_optm55.s")

if __name__ == '__main__':
    main()