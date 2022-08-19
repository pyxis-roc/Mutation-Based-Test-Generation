#!/usr/bin/env python3
#
# eqvcheck_templates.py
#
# Code templates for equivalence checks.

# TODO: pull this from the PTX semantics database?
insn_info = {
    'add_rm_ftz_f32': {'ret_type': 'float',
                       'params': ('float', 'float')},
    'abs_f32': {'ret_type': 'float',
                'params': ('float',)},
    'add_rm_ftz_sat_f32': {'ret_type': 'float',
                           'params': ('float', 'float')},
    'add_rn_f32': {'ret_type': 'float',
                   'params': ('float', 'float')},
    'add_sat_f32': {'ret_type': 'float',
                    'params': ('float', 'float')},
    'set_eq_ftz_s32_f32': {'ret_type': 'int32_t',
                           'params': ('float', 'float')},
    'set_ge_f32_f32': {'ret_type': 'float',
                       'params': ('float', 'float')},
    'set_gt_s32_f32': {'ret_type': 'int32_t',
                       'params': ('float', 'float')},
    'set_gt_u32_f32': {'ret_type': 'uint32_t',
                       'params': ('float', 'float')},
    'setp_ge_f32': {'ret_type': 'unsigned int',
                    'params': ('float', 'float')},
    'sqrt_rm_f32': {'ret_type': 'float',
                    'params': ('float', )},
    'sub_rn_ftz_sat_f32': {'ret_type': 'float',
                           'params': ('float', 'float')},
    'sub_rz_ftz_sat_f32': {'ret_type': 'float',
                           'params': ('float', 'float')}
    }


class TyHelper:
    def __init__(self, tyname):
        self.tyname = tyname

    def nondet_fn(self):
        return f"nondet_{self.tyname.replace(' ', '_')}()"

    def nondet_fn_decl(self):
        return f"{self.tyname} {self.nondet_fn()};"

    def check_eqv(self, v1, v2):
        return f"{v1} == {v2}"

class FloatTyHelper(TyHelper):
    def check_eqv(self, v1, v2):
        return f"(isnan({v1}) && isnan({v2})) || ({v1} == {v2})"


ty_helpers = {}
ty_helpers["float"] = FloatTyHelper('float')
ty_helpers["double"] = FloatTyHelper('double')
ty_helpers.update(dict([(ty, TyHelper(ty)) for ty in ["int32_t", "uint32_t", "unsigned int"]]))


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
        return insn_info[self.insn.insn]['ret_type']

    def get_param_types(self):
        return insn_info[self.insn.insn]['params']

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
