#!/usr/bin/env python3
#
# eqvcheck_templates.py
#
# Code templates for equivalence checks.

insn_info = {
    'add_rm_ftz_f32': {'ret_type': 'float',
                       'params': ('float', 'float')}
    }

class EqvCheckTemplate:
    def __init__(self, insn, mutated_fn):
        self.fn_name = "main"
        self.insn = insn
        self.mutated_fn = mutated_fn

    def get_decls(self):
        rty = self.get_ret_type()
        if rty in {"float"}:
            return [f"{rty} nondet_{rty}();"]
        else:
            return []

    def get_ret_type(self):
        return insn_info[self.insn.insn]['ret_type']

    def get_param_types(self):
        return insn_info[self.insn.insn]['params']

    def get_param_init(self, param_names):
        out = []
        for p, ty in zip(param_names, self.get_param_types()):
            if ty == "float":
                out.append(f"  {p} = nondet_float();")
            else:
                raise NotImplementedError(f"Symbolic initialization of type not implemented: {ty}")
        return out

    def get_ret_check(self, rv_orig, rv_mut):
        rty = self.get_ret_type()

        if rty == "float":
            return f"isnan(({rv_orig}) && isnan({rv_mut})) || ({rv_orig} == {rv_mut})"
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
