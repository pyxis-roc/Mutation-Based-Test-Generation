#!/usr/bin/env python3
#
# eqvcheck_templates.py
#
# Code templates for equivalence checks.

from insninfo import insn_info

ty_conv = {'u8': 'uint8_t',
           'u16': 'uint16_t',
           'u32': 'uint32_t',
           'u64': 'uint64_t',

           'b8': 'uint8_t',
           'b16': 'uint16_t',
           'b32': 'uint32_t',
           'b64': 'uint64_t',

           'f32': 'float',
            's8': 'int8_t',
           's16': 'int16_t',
           's32': 'int32_t',
           's64': 'int64_t',
           'f64': 'double',
           'pred': 'unsigned int',
           'cc_reg': 'struct cc_register'}

class TyHelper:
    def __init__(self, tyname):
        self.tyname = tyname

    def nondet_fn(self):
        return f"nondet_{self.tyname.replace(' ', '_')}()"

    def domain_restrict(self, v):
        return None

    def nondet_fn_decl(self):
        return f"{self.tyname} {self.nondet_fn()};"

    def struct_unpacker(self):
        # this is going to cause issues if struct has padding.

        if self.tyname == 'float':
            return 'f'
        elif self.tyname == 'double':
            return 'd'
        elif self.tyname == 'int8_t':
            return 'b'
        elif self.tyname == 'uint8_t':
            return 'B'
        elif self.tyname == 'int8_t':
            return 'b'
        elif self.tyname == 'uint16_t':
            return 'H'
        elif self.tyname == 'int16_t':
            return 'h'
        elif self.tyname in ('uint32_t', 'unsigned int'):
            return 'I'
        elif self.tyname == 'int32_t':
            return 'i'
        elif self.tyname == 'uint64_t':
            return 'Q'
        elif self.tyname == 'int64_t':
            return 'q'
        else:
            raise NotImplementedError(f"Need struct unpacker for {self.tyname}")

    def check_eqv(self, v1, v2):
        return f"{v1} == {v2}"

class FloatTyHelper(TyHelper):
    def check_eqv(self, v1, v2):
        return f"(isnan({v1}) && isnan({v2})) || ({v1} == {v2})"

class CCRegTyHelper(TyHelper):
    def __init__(self, tyname):
        self.tyname = tyname

    def domain_restrict(self, v):
        return f"{v}.cf == 0 || {v}.cf == 1"

    def nondet_fn(self):
        return f"nondet_struct_ccreg()"

    def nondet_fn_decl(self):
        return f"struct cc_register {self.nondet_fn()};"

    def check_eqv(self, v1, v2):
        return f"{v1}.cf == {v2}.cf"


ty_helpers = {}
ty_helpers["float"] = FloatTyHelper('float')
ty_helpers["double"] = FloatTyHelper('double')
ty_helpers.update(dict([(ty, TyHelper(ty)) for ty in [
    "int8_t", "uint8_t", "uint16_t", "int16_t",
    "int64_t", "uint64_t", "int32_t", "uint32_t",
    "unsigned int"]]))

ty_helpers["struct cc_register"] = CCRegTyHelper("struct cc_register")

class EqvCheckTemplate:
    def __init__(self, insn, mutated_fn):
        self.fn_name = "main"
        self.insn = insn
        self.mutated_fn = mutated_fn

    def get_decls(self):
        dty = [self.get_ret_type()]
        dty.extend(self.get_param_types())
        dty = set(dty)

        out = []
        for i in dty:
            tyh = ty_helpers[i]
            out.append(tyh.nondet_fn_decl())

        out.append("\n")
        return out

    def get_ret_type(self):
        ty = insn_info[self.insn.insn]['output_types']
        if len(ty) > 1:
            assert len(ty) == 2 and ty[1] == "cc_reg", ty[1]

        return ty_conv[ty[0]]

    def get_param_types(self):
        ty = insn_info[self.insn.insn]['arg_types']
        return [ty_conv[t] for t in ty]

    def get_output_types(self):
        ty = insn_info[self.insn.insn]['output_types']
        return [ty_conv[t] for t in ty]

    def get_param_init(self, param_names):
        out = []
        for p, ty in zip(param_names, self.get_param_types()):
            if ty in ty_helpers:
                tyh = ty_helpers[ty]
                out.append(f"  {p} = {tyh.nondet_fn()};")
                rst = tyh.domain_restrict(p)
                if rst is not None:
                    out.append(f"  __CPROVER_assume({rst});")
            else:
                raise NotImplementedError(f"Symbolic initialization of type not implemented: {ty}")
        return out

    def get_ret_check(self, rv_orig, rv_mut):
        rty = self.get_ret_type()

        if rty in ty_helpers:
            return ty_helpers[rty].check_eqv(rv_orig, rv_mut)
        else:
            raise NotImplementedError(f"Checks for return type not implemented: {rty}")

    def get_out_checks(self, out_offset, orig_call_args, mut_call_args,
                       template=lambda cond: f"  assert({cond});"):

        oty = self.get_output_types()[1:]
        out = []
        for idx, ty in enumerate(oty, 1):
            if ty in ty_helpers:
                # strip the & in front
                tyh = ty_helpers[ty]
                out.append(template(tyh.check_eqv(orig_call_args[idx+out_offset-1][1:],
                                                  mut_call_args[idx+out_offset-1][1:])))
            else:
                raise NotImplementedError(f"Checks for out type not implemented: {ty}")

        return out

    def get_inout_checks(self, orig_call_args, mut_call_args,
                         template=lambda cond: f"  assert({cond});"):
        inout = insn_info[self.insn.insn].get('inout_args', [])
        ty = insn_info[self.insn.insn]['arg_types']

        out = []
        for idx in inout:
            at = ty_conv[ty[idx]]
            if at in ty_helpers:
                # strip the & in front
                tyh = ty_helpers[at]
                out.append(template(tyh.check_eqv(orig_call_args[idx][1:], mut_call_args[idx][1:])))
            else:
                raise NotImplementedError(f"Checks for inout type not implemented: {at}")

        return out

    def get_template(self):
        if self.fn_name == "main":
            fnr = "int"
        else:
            fnr = "void"

        out = []
        out.append(f"{fnr} {self.fn_name}(void) {{")

        origargs = []
        mutargs = []
        initargs = []
        mutinit = []
        inout = set(insn_info[self.insn.insn].get('inout_args', set()))

        for i, ty in enumerate(self.get_param_types()):
            if i in inout:
                origargs.append(f"&arg{i}")
                mutargs.append(f"&mut_arg{i}")

                initargs.append(f"arg{i}")
                mutinit.append(f"  mut_arg{i} = arg{i};")

                out.append(f"  {ty} mut_{initargs[i]};")
            else:
                origargs.append(f"arg{i}")
                mutargs.append(f"arg{i}")
                initargs.append(f"arg{i}")

            out.append(f"  {ty} {initargs[i]};")

        ret = ["ret_orig", "ret_mut"]
        rty = self.get_ret_type()
        for r in ret:
            out.append(f"  {rty} {r};")

        # multiple output types are usually tacked on to the end?
        # first output type is ret
        out_offset = len(origargs)
        for i, oty in enumerate(self.get_output_types()[1:], 0):
            if oty == 'struct cc_register':
                out.append(f'  {oty} out{i}, mut_out{i};')
                origargs.append(f"&out{i}")
                mutargs.append(f"&mut_out{i}")
            else:
                raise NotImplementedError(f"{oty} not yet handled")

        out.extend(self.get_param_init(initargs))
        out.extend(mutinit)

        assert len(ret) == 2, ret
        origcall_args = ", ".join(origargs)
        mutcall_args = ", ".join(mutargs)
        out.append(f"  {ret[0]} = {self.insn.insn_fn}({origcall_args});")
        out.append(f"  {ret[1]} = {self.mutated_fn}({mutcall_args});")

        out.append(f"  assert({self.get_ret_check(ret[0], ret[1])});")
        if len(inout):
            out.extend(self.get_inout_checks(origargs, mutargs))

        out.extend(self.get_out_checks(out_offset, origargs, mutargs))

        out.append("}")
        return "\n".join(out)
