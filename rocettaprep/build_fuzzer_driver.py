#!/usr/bin/env python3

import argparse
from rocprepcommon import *
from build_single_insn import Insn
from eqvcheck_templates import insn_info, ty_helpers, ty_conv
from mutate import get_mutation_helper, get_mutators
import shutil
from build_single_insn import PTXSemantics
from parsl.app.app import python_app
import parsl
import sys

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
        assert len(t) == 1
        return ty_conv[t[0]]

    def get_ret_check(self, rv_orig, rv_mut):
        rty = self.get_ret_type()

        if rty in ty_helpers:
            return ty_helpers[rty].check_eqv(rv_orig, rv_mut)
        else:
            raise NotImplementedError(f"Checks for return type not implemented: {rty}")

    def get_param_types(self):
        t = insn_info[self.insn.insn]['arg_types']
        return [ty_conv[tt] for tt in t]

    def get_template(self):
        out = []
        out.append("#ifdef __cplusplus")
        out.append(f'extern "C"')
        out.append("#endif")
        out.append(f'int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {{')

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
        out.append("  if(Size != sizeof(struct arg_struct)) return 0;")

        # packing check
        out.append(f"  assert(sizeof(struct arg_struct) == {szcheck});")
        out.append("")

        # WARNING: ALIGNMENT ISSUES POSSIBLY?
        # this assumes machine has no alignment restrictions.
        out.append("  args = (struct arg_struct *) Data;")

        ret = ["ret_orig", "ret_mut"]
        rty = self.get_ret_type()
        for r in ret:
            out.append(f"  {rty} {r};")

        out.append("")

        assert len(ret) == 2, ret
        call_args = ", ".join(args)
        out.append(f"  {ret[0]} = {self.insn.insn_fn}({call_args});")
        out.append(f"  {ret[1]} = {self.mutated_fn}({call_args});")

        out.append(f"  assert({self.get_ret_check(ret[0], ret[1])});")

        out.append("return 0;")
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
        out.append(f"  assert(sizeof(struct arg_struct) == {szcheck});")
        out.append("")

        out.append("  args = (struct arg_struct *) Data;")

        out.append("  srand(Seed);")

        for arg, ty in zip(args, self.get_param_types()):
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

def build_fuzzer_driver(wp, insn, muthelper, setup_only = False, fuzzer = 'simple', parallel = True):
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

        if parallel:
            for x in out:
                print(x.result(), file=sys.stderr)

        fb.generate_fuzzer_makefile()


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

    parsl.load(config)

    for insn in get_instructions(args.insn):
        print(insn, file=sys.stderr)
        i = Insn(insn)
        build_fuzzer_driver(wp, i, muthelper, setup_only = args.driver_only, fuzzer = args.fuzzer, parallel = not args.no_parallel)
