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
           'pred': 'unsigned int'}

class TyHelper:
    def __init__(self, tyname):
        self.tyname = tyname

    def nondet_fn(self):
        return f"nondet_{self.tyname.replace(' ', '_')}()"

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


ty_helpers = {}
ty_helpers["float"] = FloatTyHelper('float')
ty_helpers["double"] = FloatTyHelper('double')
ty_helpers.update(dict([(ty, TyHelper(ty)) for ty in [
    "int8_t", "uint8_t", "uint16_t", "int16_t",
    "int64_t", "uint64_t", "int32_t", "uint32_t",
    "unsigned int"]]))


class EqvCheckTemplate:
    def __init__(self, insn, mutated_fn):
        self.fn_name = "main"
        self.insn = insn
        self.mutated_fn = mutated_fn

    def get_decls(self):
        rty = self.get_ret_type()
        tyh = ty_helpers[rty]

        return [tyh.nondet_fn_decl()]

    def get_ret_type(self):
        ty = insn_info[self.insn.insn]['output_types']
        assert len(ty) == 1
        return ty_conv[ty[0]]

    def get_param_types(self):
        ty = insn_info[self.insn.insn]['arg_types']
        return [ty_conv[t] for t in ty]

    def get_param_init(self, param_names):
        out = []
        for p, ty in zip(param_names, self.get_param_types()):
            if ty in ty_helpers:
                tyh = ty_helpers[ty]
                out.append(f"  {p} = {tyh.nondet_fn()};")
            else:
                raise NotImplementedError(f"Symbolic initialization of type not implemented: {ty}")
        return out

    def get_ret_check(self, rv_orig, rv_mut):
        rty = self.get_ret_type()

        if rty in ty_helpers:
            return ty_helpers[rty].check_eqv(rv_orig, rv_mut)
        else:
            raise NotImplementedError(f"Checks for return type not implemented: {rty}")

    def get_template(self):
        if self.fn_name == "main":
            fnr = "int"
        else:
            fnr = "void"

        out = []
        out.append(f"{fnr} {self.fn_name}(void) {{")

        args = []
        for i, ty in enumerate(self.get_param_types()):
            args.append(f"arg{i}")
            out.append(f"  {ty} {args[i]};")

        ret = ["ret_orig", "ret_mut"]
        rty = self.get_ret_type()
        for r in ret:
            out.append(f"  {rty} {r};")

        out.extend(self.get_param_init(args))

        assert len(ret) == 2, ret
        call_args = ", ".join(args)
        out.append(f"  {ret[0]} = {self.insn.insn_fn}({call_args});")
        out.append(f"  {ret[1]} = {self.mutated_fn}({call_args});")

        out.append(f"  assert({self.get_ret_check(ret[0], ret[1])});")
        out.append("}")
        return "\n".join(out)
