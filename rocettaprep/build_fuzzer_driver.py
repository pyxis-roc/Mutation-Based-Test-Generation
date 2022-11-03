#!/usr/bin/env python3

import argparse
from rocprepcommon import *
from build_single_insn import Insn
from eqvcheck_templates import insn_info, ty_helpers, ty_conv, StructRetvalTyHelper
from mutate import get_mutation_helper, get_mutators
import shutil
from build_single_insn import PTXSemantics
from parsl.app.app import python_app, join_app, bash_app
import parsl
import sys
import struct

class FuzzerTemplateSimple:
    """Fuzzer template for simple scheme where we rely on the fuzzer to do
       all the work of generating inputs."""

    def __init__(self, insn, mutated_fn):
        self.insn = insn
        self.mutated_fn = mutated_fn

    def get_decls(self):
        return ["#include <assert.h>"]

    def get_ret_type(self):
        t = insn_info[self.insn.insn]['output_types']
        if len(t) > 1:
            if len(t) == 2 and t[1] == "pred":
                self.output_types = list([ty_conv[tt] for tt in t])
                return f"struct retval_{self.insn.insn}"

            assert len(t) == 2 and t[1] == "cc_reg", t[1]

        return ty_conv[t[0]]

    def get_output_types(self):
        ty = insn_info[self.insn.insn]['output_types']
        return [ty_conv[t] for t in ty]

    def get_ret_check(self, rv_orig, rv_mut):
        rty = self.get_ret_type()

        if rty in ty_helpers:
            return ty_helpers[rty].check_eqv(rv_orig, rv_mut)
        elif rty.startswith('struct retval_'):
            return StructRetvalTyHelper(rty, self.output_types).check_eqv(rv_orig, rv_mut)
        else:
            raise NotImplementedError(f"Checks for return type not implemented: {rty}")

    def get_param_types(self):
        t = insn_info[self.insn.insn]['arg_types']
        return [ty_conv[tt] for tt in t]

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

    def get_out_checks(self, out_offset, orig_call_args, mut_call_args,
                       template=lambda cond: f"  assert({cond});"):

        oty = self.get_output_types()[1:]
        out = []
        for idx, ty in enumerate(oty, 1):
            if ty == 'struct cc_register':
                # strip the & in front
                tyh = ty_helpers[ty]
                out.append(template(tyh.check_eqv(orig_call_args[idx+out_offset-1][1:],
                                                  mut_call_args[idx+out_offset-1][1:])))
            elif ty == 'unsigned int':
                # output is in a struct, so will be checked separately
                pass
            else:
                raise NotImplementedError(f"Checks for out type not implemented: {ty}")

        return out

    def get_template(self):
        out = []
        out.append("#ifdef __cplusplus")
        out.append(f'extern "C"')
        out.append("#endif")
        out.append(f'int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {{')

        callargs = []
        mutargs = []
        mutinit = []
        domchk = []
        sz = []

        inout = set(insn_info[self.insn.insn].get('inout_args', set()))

        # use a struct to load args, with the possible caveat that any
        # packing might increase search space unnecessarily?

        out.append("  struct arg_struct {")
        for i, ty in enumerate(self.get_param_types()):
            if i in inout:
                callargs.append(f"&args->arg{i}")
                mutargs.append(f"&mut_arg{i}")
                mutinit.append(f"  {ty} mut_arg{i} = args->arg{i};")
            else:
                callargs.append(f"args->arg{i}")
                mutargs.append(f"args->arg{i}")

            cond = ty_helpers[ty].domain_restrict(f"args->arg{i}")
            if cond is not None:
                domchk.append(f"  if(!({cond})) return 0;")

            out.append(f"    {ty} arg{i};")
        out.append("  } *args;")

        out.append("  if(Size != sizeof(struct arg_struct)) return 0;")

        # WARNING: ALIGNMENT ISSUES POSSIBLY?
        # this assumes machine has no alignment restrictions.
        out.append("  args = (struct arg_struct *) Data;")
        out.extend(mutinit)

        out.extend(domchk)

        ret = ["ret_orig", "ret_mut"]
        rty = self.get_ret_type()
        for r in ret:
            out.append(f"  {rty} {r};")

        out.append("")

        # multiple output types are usually tacked on to the end?
        # first output type is ret
        out_offset = len(callargs)
        for i, oty in enumerate(self.get_output_types()[1:], 0):
            if oty == 'struct cc_register':
                out.append(f'  {oty} out{i}, mut_out{i};')
                callargs.append(f"&out{i}")
                mutargs.append(f"&mut_out{i}")
            elif oty == 'unsigned int': # pred x pred
                assert rty.startswith('struct retval_'), rty
            else:
                raise NotImplementedError(f"{oty} not yet handled")


        assert len(ret) == 2, ret
        origcall_args = ", ".join(callargs)
        mutcall_args =  ", ".join(mutargs)

        out.append(f"  {ret[0]} = {self.insn.insn_fn}({origcall_args});")
        out.append(f"  {ret[1]} = {self.mutated_fn}({mutcall_args});")

        out.append(f"  assert({self.get_ret_check(ret[0], ret[1])});")

        # inout checks

        if len(inout):
            out.extend(self.get_inout_checks(callargs, mutargs))

        out.extend(self.get_out_checks(out_offset, callargs, mutargs))

        out.append("  return 0;")
        out.append("}")

        return "\n".join(out)

class FuzzerTemplateCustom(FuzzerTemplateSimple):
    """Fuzzer template for Custom mutator that does stratified sampling."""

    def get_decls(self):
        return super().get_decls() + ['#include "strata_sampler.h"']

    def get_template(self):
        out = []
        out.append("#ifdef __cplusplus")
        out.append(f'extern "C"')
        out.append("#endif")
        out.append(f'int LLVMFuzzerCustomMutator(const uint8_t *Data, size_t Size, size_t MaxSize, unsigned int Seed) {{')

        args = []
        sz = []

        # use a struct to load args, with the possible caveat that any
        # packing might increase search space unnecessarily?

        out.append("  struct arg_struct {")

        for i, ty in enumerate(self.get_param_types()):
            args.append(f"args->arg{i}")
            sz.append(f"sizeof({ty})")
            out.append(f"    {ty} arg{i};")

        out.append("  } *args;")

        szcheck = "+".join(sz)
        out.append("  if(MaxSize < sizeof(struct arg_struct)) return 0;")

        # packing check
        #out.append(f"  assert(sizeof(struct arg_struct) == {szcheck});")
        out.append("")

        out.append("  args = (struct arg_struct *) Data;")

        out.append("  srand(Seed);")

        for arg, ty in zip(args, self.get_param_types()):
            if ty == 'unsigned int':
                ty = 'uint32_t'
            elif ty == 'struct cc_register':
                ty = 'cc_register'

            out.append(f"  {arg} = sample_{ty}();")

        out.append("return sizeof(struct arg_struct);")
        out.append("}")

        fn = "\n".join(out) + "\n\n"

        fn += super().get_template()

        return fn

class FuzzerBuilder:
    def __init__(self, wp, insn, muthelper, template = 'simple'):
        self.wp = wp
        self.insn = insn
        self.muthelper = muthelper
        self.template = template

    def add_padding(self, structfmt):
        max_size = 0
        max_fmt = None
        for x in structfmt:
            if struct.calcsize(x) > max_size:
                max_size = struct.calcsize(x)
                max_fmt = x

        # python does not add end padding, but C does.
        return '@' + structfmt + f'0{max_fmt}'

    def setup(self):
        # testfile = self.wp.workdir / self.insn.working_dir / self.insn.test_file
        # with open(testfile, "r") as f:
        #     self.testfile_contents = f.readlines()

        odir = self.wp.workdir / self.insn.working_dir / f"libfuzzer_{self.template}"

        if not odir.exists():
            odir.mkdir()

        if self.template == 'simple':
            # generate driver
            tmpl = FuzzerTemplateSimple(self.insn, "mutated_fn")
        elif self.template == 'custom':
            tmpl = FuzzerTemplateCustom(self.insn, "mutated_fn")

        with open(odir / self.insn.test_file, "w") as f:
            f.write("\n".join(tmpl.get_decls()) + "\n")
            f.write(tmpl.get_template())

        with open(odir / "struct_info.txt", "w") as f:
            ptypes = tmpl.get_param_types()
            struct_fmt = "".join([ty_helpers[pty].struct_unpacker() for pty in ptypes])
            struct_fmt = self.add_padding(struct_fmt)

            f.write(struct_fmt)

    def process_mutfile(self, mutfile):
        src = self.wp.workdir / self.insn.working_dir / "eqchk" / mutfile.name
        dst = self.wp.workdir / self.insn.working_dir / f"libfuzzer_{self.template}" / mutfile.name

        # this expects the equivalence checker to have run first
        if not src.exists():
            raise FileNotFoundError(f"{src} not found, run build_eqvcheck_driver.py to generate it")

        # TODO: add decls for kill and pid
        shutil.copy(src, dst)

        return dst

    def generate_fuzzer_makefile(self):
        def clang_compiler(srcfiles, obj, cflags, libs):
            cmd = ["clang-13"] # clang-12 should also work?
            cmd.extend(cflags)
            cmd.extend(["-I", self.wp.csemantics.parent.absolute()])

            if self.template == 'custom':
                cmd.extend(["-I", self.wp.workdir / 'samplers'])

            cmd.extend(filter(lambda x: x is not None, srcfiles))
            cmd.extend(["-o", obj])
            cmd.extend(libs)
            return cmd

        odir = self.wp.workdir / self.insn.working_dir / f"libfuzzer_{self.template}"
        srcs = [x['src'] for x in self.muthelper.get_mutants(self.insn)]

        p = PTXSemantics(self.wp.csemantics, []) # since we only want the compiler commands

        out = []

        with open(odir / "Makefile", "w") as f:
            all_targets = " ".join([s[:-2] for s in srcs])

            f.write("CFLAGS ?= -g -O3\n\n")
            f.write(f"all: {all_targets}\n\n")

            for s in srcs:
                target = s[:-2] # remove .c
                f.write(f"{target}: {s}\n\t")
                cmds = p.get_compile_command_primitive(str(s), None,
                                                       target, cflags=["${CFLAGS}",
                                                                       "-fsanitize=fuzzer"],                                                       compiler_cmd = clang_compiler)

                f.write("\n\t".join([" ".join([str(cc) for cc in c])
                                     for c in cmds]))
                f.write("\n\n")

@python_app
def run_process_mutfile(fb, mutsrc):
    dst = fb.process_mutfile(mutsrc)
    return dst

def build_fuzzer_driver(wp, insn, muthelper, setup_only = False, fuzzer = 'simple', parallel = True, nowait = True):
    mutants = muthelper.get_mutants(insn)
    mutsrcs = [wp.workdir / insn.working_dir / muthelper.srcdir / x['src'] for x in mutants]

    fb = FuzzerBuilder(wp, insn, muthelper, template=fuzzer)
    fb.setup()
    if not setup_only:
        out = []
        for s in mutsrcs:
            if parallel:
                out.append(run_process_mutfile(fb, s))
            else:
                print(fb.process_mutfile(s), file=sys.stderr)

        fb.generate_fuzzer_makefile()

        if parallel:
            if nowait:
                return out

            for x in out:
                print(x.result(), file=sys.stderr)

@bash_app
def run_fuzzer_driver(script, workdir, insn, mutator, fuzzer, driver_only):
    # plain python apps seem to have limited scalability with the threadpoolexecutor
    # maybe GIL? so use bash app.
    if driver_only:
        driver_only = '--driver-only'
    else:
        driver_only = ''

    return f'{script} --np --insn {insn} --mutator {mutator} --fuzzer {fuzzer} {driver_only} {workdir}'

if __name__ == "__main__":
    from setup_workdir import WorkParams
    from runconfig import config

    p = argparse.ArgumentParser(description="Generate LLVM fuzzer drivers")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--driver-only", action="store_true", help="Only generate the driver")
    p.add_argument("--fuzzer", choices=['simple', 'custom'], default='simple')
    p.add_argument("--np", dest='no_parallel', help="Process serially", action="store_true")

    args = p.parse_args()
    wp = WorkParams.load_from(args.workdir)
    muthelper = get_mutation_helper(args.mutator, wp)

    if not args.no_parallel:
        parsl.load(config)

    p = []
    for insn in get_instructions(args.insn):
        print(insn, file=sys.stderr)
        i = Insn(insn)
        if args.no_parallel:
            build_fuzzer_driver(wp, i, muthelper, setup_only = args.driver_only, fuzzer = args.fuzzer, parallel = not args.no_parallel)
        else:
            p.append(run_fuzzer_driver(__file__, args.workdir, insn, args.mutator, args.fuzzer, args.driver_only))

    if not args.no_parallel:
        for t in p:
            print(t.result(), file=sys.stderr)
