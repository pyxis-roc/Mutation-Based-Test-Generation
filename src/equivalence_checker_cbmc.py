# This is the component that will iteratively run the desired equivalence checker between the oracle program and all the survived mutated programs
# This component's output will be a set of new test cases to cover the desired mutations.

# TODO: perhaps create a csv pairing test cases with mutation code generated by MUSIC

import numpy
import os
import subprocess
from os.path import isfile, join
from program_manipulation import ProgramManipulator 
import json
import time
import math
import struct
import multiprocessing as mp
from pathlib import Path

class EquivalenceChecker(object):

    def __init__(self, oracle_program, function_name, survived_mutations, input_file, new_input_filename="new_inputs.txt", backend="", path_to_fakeheaders="pycparser/utils/fake_libc_include", analysis=True, survived_mutation_outputs=None, create_new_suite=False, working_directory = "working_directory"):
        """
        Args:
        oracle_program is a path to the program.
        survived_mutations is a path to the directory of survived mutated programs.
        checker is type of equivalence checker.
        We currently support the following equivalence checkers:
        CBMC = "Equivalence Check via --trace flag in CBMC
        """
        self.oracle_program = oracle_program
        self.function_name = function_name
        self.survived_mutations = survived_mutations
        self.path_to_fakeheaders = path_to_fakeheaders
        # dynamic values
        self.oracle_manipulator = ProgramManipulator(oracle_program, path_to_fakeheaders, other_headers=[f"-I{working_directory}"])
        self.oracle_function = self.oracle_manipulator.get_function(function_name)
        self.inputs = EquivalenceChecker.process_inputs(input_file) if input_file is not None else []
        self.function_inputs = self.oracle_manipulator.get_function_inputs(function_name)
        self.function_return_type = self.oracle_manipulator.get_function_return_type(function_name)
        self.backend = backend
        self.new_input_filename = new_input_filename
        self.do_analysis = analysis
        self.survived_mutation_outputs = survived_mutation_outputs
        self.working_dir = working_directory

    # stolen from smt2utils
    @staticmethod
    def conform_c(x):
        """Conform to C's %0.13a"""

        if x == "0x0.0p+0":
            return "0x0.0000000000000p+0"
        elif x == "-0x0.0p+0":
            return "-0x0.0000000000000p+0"
        else:
            return x

    @staticmethod
    def float_hex2(x):
        """Replacement for float.hex that does not discards sign from NaN"""

        if math.isnan(x) and (math.copysign(1., x) == -1.0):
            return "-nan"

        return x.hex()

    @staticmethod
    def bin_to_float(binary):
        return EquivalenceChecker.conform_c(EquivalenceChecker.float_hex2(struct.unpack('!f',struct.pack('!I', int(binary, 2)))[0]))

    @staticmethod
    def bin_to_int(b):
        return int(b, 2)

    @staticmethod
    def classify_float(x):
        fp = numpy.single(x) # equivalent to c float.
        # classifications are inf, nan, normal, subnormal, zero, unknown
        if fp == 0.0:
            return "zero"
        if numpy.isinf(fp):
            return "Inf"
        if numpy.isnan(fp):
            return "NaN"
        else:
            fmin_normalized = numpy.finfo(type(fp)).tiny # smallest normal representation
            fp_is_subnormal = numpy.isfinite(fp) and fp != 0 and abs(fp) < fmin_normalized
            if fp_is_subnormal:
                return "subnormal"
            else:
                return "normal"
        return "unknown"
    
    @staticmethod
    def create_html_file(mutated_function, oracle_function, input_values, input_classifications, mut_name):
        html_head = f"""<head> 
               <meta charset=\"UTF-8\">
        <title>Analysis for {mut_name}</title>
        <style>
        </style>
        </head>"""
        html_body = "<body>"
        # script for prettyfing code
        html_body += """<script src=\"https://cdn.jsdelivr.net/gh/google/code-prettify@master/loader/run_prettify.js\"></script>"""
        html_body += f"<h1>Analysis for {mut_name}</h1>"
        html_body += f"<h2>Input Information</h2>"
        # create input content
        input_content = ""
        for i in range(len(input_values)):
            input_content += f"<h4>Input {i+1}: {input_values[i]}\nClassified as: {input_classifications[i]}</h4>"
        html_body += input_content
        
        # add outputs (should be equal)
        # output_content = ""
        # output_content += f"\n<h4>Oracle Output: {oracle_output}\nClassified as: {EquivalenceChecker.classify_float(float.fromhex(oracle_output))}</h4>"
        # output_content += f"\n<h4>Mutated Output: {mutated_output}\nClassified as: {EquivalenceChecker.classify_float(float.fromhex(mutated_output))}</h4>"
        # html_body += output_content


        # add programs #TODO make this side by side
        html_body += "<h3>Oracle Function</h3>"
        html_body += f"""<pre class=\"prettyprint\">{oracle_function}</pre>"""
        html_body += "<h3>Mutated Function</h3>"
        html_body += f"""<pre class=\"prettyprint\">{mutated_function}</pre>"""
        
        html_body += "</body>"
        # if test_suite:
        #     test_suite_string = "".join(test_suite)
        #     html_body += f"<p>{test_suite_string}</p>"
        # if mutation_outputs:
        #     mut_out_string = "".join(mutation_outputs)
        #     html_body += f"<p>{mut_out_string}</p>"

        html = html = f"""<html lang="en"> {html_head} {html_body} </html>"""
        f = open(os.path.join("./analysis",f"{mut_name}.html"), "w+")
        f.write(html)
        f.close()

    def create_analysis(self, new_inputs):
        # create analysis directory
        print("Analyzing")
        if not os.path.isdir("./analysis"):
	        os.mkdir("./analysis")
        else:
	        os.system("rm -rf analysis")
	        os.mkdir("./analysis")
        print(new_inputs)
        for i in new_inputs:
            if i is not None:
                input_values = i[0]
                mutation = i[1]
                if input_values is not None and mutation is not None:
                    # extract mutated function as a string
                    mutation_manipulator = ProgramManipulator(mutation, self.path_to_fakeheaders, other_headers=[f"-I{self.working_dir}"])
                    mutated_func = mutation_manipulator.get_function(self.function_name)
                            
                    # classify inputs
                    # TODO: only float, what about int?
                    classifications = []
                    for i_float in input_values:
                        classifications.append(EquivalenceChecker.classify_float(float.fromhex(i_float)))
                    # create html file 
                    html_file = EquivalenceChecker.create_html_file(mutated_func, self.oracle_function, input_values, classifications, ProgramManipulator.extract_last_file_from_prog_path(mutation))
    
    @staticmethod
    def process_inputs(input_file):
        # create array of inputs
        inputs = []
        file_lines = open(input_file, "r").readlines()
        for input_line in file_lines:
            input_set = []
            splitted = input_line.split()
            for input in splitted:
                input_set.append(input)
            inputs.append(input_set)
            input_set = []
        # return array
        return inputs
    
    @staticmethod
    def get_first_value_from_trace(trace, variable_name, trace_reversed=False):
        value = None
        try:
            if trace_reversed:
                for event in reversed(trace):
                    if event.get("assignmentType") == "variable" and event.get("lhs") == variable_name:
                        value = event["value"]
                        break
            else:
                for event in trace:
                    if event.get("assignmentType") == "variable" and event.get("lhs") == variable_name:
                        value = event["value"]
            if value is not None:
                if value["name"] == "integer":
                    return EquivalenceChecker.bin_to_int(value["binary"])
                elif value["name"] == "float":
                    return EquivalenceChecker.bin_to_float(value["binary"])
        except Exception as e:
            print(e)
            print(f"Could not find {variable_name} in trace")
            pass

    def create_instrumented_program(self, mutated_program):
        # create .c file
        filename = f"equivalence_check_{ProgramManipulator.extract_last_file_from_prog_path(mutated_program)}.c"
        f = open(os.path.join(self.working_dir, filename), "w+")
        # add includes        
        includes = ProgramManipulator.get_all_includes(mutated_program)

        # extract mutated function from mutated program
        # Create manipulator for mutated program
        mutated_pm = ProgramManipulator(mutated_program, self.path_to_fakeheaders, other_headers=[f"-I{self.working_dir}"])
        mutated_function = mutated_pm.get_function(self.function_name)
        mutated_function_name = "mutated_function"
        mutated_function = ProgramManipulator.rename_function(mutated_function, self.function_name, mutated_function_name)
        # add them both to .c file
        # add main method to nondeterministically equal both functions
        main_method = ["int main(){"]
        # for each input 

        counter = 0
        param_string = ""
        for i in self.function_inputs:
            main_method.append(f"{i[1]} variable_{counter};")
            param_string += f"variable_{counter},"
            counter+=1
        
        # remove trailing comma
        param_string = param_string[:-1]

        # create main method
        main_method.append(f"{self.function_return_type} result = {self.function_name}({param_string});")
        main_method.append(f"{self.function_return_type}  mutated_result = {mutated_function_name}({param_string});")
        # set them equal so that --trace flag gives counterexample where they are not equal.
        main_method.append("assert(result == mutated_result);")
        main_method.append("return 0;")
        main_method.append("}")

        # construct program
        program = ""
        program += "".join(includes)
        program += self.oracle_function + "\n"
        program += mutated_function
        program += "\n".join(main_method)
        f.write(program)
        f.close()
        # return program file name
        return filename



    def get_counterexample_from_CBMC(self, instrumented_program, mutation_name):
        cbmc_json_filename = f"cbmc_output_{ProgramManipulator.extract_last_file_from_prog_path(mutation_name)}.json"
        subprocess.call(f"cbmc --trace {instrumented_program} {self.backend} --json-ui > {cbmc_json_filename}", shell=True, cwd=self.working_dir)
        cbmc_results = open(os.path.join(self.working_dir, cbmc_json_filename), "r").read()
        cbmc_json = json.loads(cbmc_results)
        trace = None
        print(cbmc_json_filename)
        if cbmc_json is not None:
            if "cProverStatus" in cbmc_json[-1] and cbmc_json[-1]["cProverStatus"] == "success":
                print(f"{mutation_name} is semantically identical to source!")

        for value in cbmc_json:
            if "result" in value:
                try:
                    trace = value["result"][0]["trace"]
                except Exception as e:
                    print(type(e), str(e))
                    print(f"Trace not found for {mutation_name}")
                    return None
        if trace == None:
            print((f"CBMC Result not found for {mutation_name}"))
            return None

        # get number of inputs from ProgramManipulator, loop over and interprolate the number into variable_
        counter_example = []
        for i in range(len(self.function_inputs)):
            value = EquivalenceChecker.get_first_value_from_trace(trace,f"variable_{i}")
            counter_example.append(value)
        mutated_output = EquivalenceChecker.get_first_value_from_trace(trace, 'mutated_result', trace_reversed=True) 
        oracle_output =  EquivalenceChecker.get_first_value_from_trace(trace, 'result', trace_reversed=True)

        # TODO: if mutated_output == oracle_output, equivalence check failed, raise exception
        if mutated_output == oracle_output:
            raise Exception(f"CBMC Trace Failed for {mutation_name}. Mutated Output = Oracle Output\n{mutated_output}={oracle_output}.")
        return counter_example


    def equivalence_check_CBMC(self, mutated_program):
        try:
            instrumented_program = self.create_instrumented_program(mutated_program)
            inputs = self.get_counterexample_from_CBMC(instrumented_program, mutated_program)
            
            return [inputs, mutated_program]
        except Exception as e:
            print("Caught Exception in equivalence_check_CBMC")
            print(e)
            pass

    def cleanup(self):
        for p in Path(self.working_dir).glob("equivalence_check*"):
            p.unlink()


    def add_to_inputs(self, input_set):
        self.inputs.append(input_set)

    def write_inputs_file(self):
        print(f"Writing input file... {self.new_input_filename}")
        result = ""
        for test in self.inputs:
            if test is not None:
                for value in test:
                    result += f"{value.strip()} "
                result += "\n"
        file = open(self.new_input_filename, "w+")
        file.write(result)
        file.close()

    def runner(self):
        self.cleanup()
        print("Begin generating counterexamples.")
        # start timer
        start = time.perf_counter()
        original_inputs = len(self.inputs)
        # loop over every program in survived mutations
        mutated_programs = [f for f in os.listdir(self.survived_mutations) if isfile(join(self.survived_mutations, f))]
        # remove other files generated by the mutator

        mutated_programs = [m for m in mutated_programs if m.endswith(".c")]
        mutated_programs = [join(self.survived_mutations, m) for m in mutated_programs if m is not None]
        print(mutated_programs)
        with mp.Pool(mp.cpu_count()) as pool:
          results = pool.map_async(self.equivalence_check_CBMC, mutated_programs).get()
        print(results)
        if self.do_analysis:
            self.create_analysis(results)

        # Remove Duplicates
        inputs_pre_deduplication = len(results)
        print(f"Total generated inputs: {inputs_pre_deduplication}")

        tmp = [i[0] for i in results if i is not None and i[0] is not None] # remove the associated mutation with the test case
        print(tmp)
        results = set(tuple(i) for i in tmp)
        inputs_post_deduplication = len(results)
        print(f"After removing duplicates: {inputs_post_deduplication}")
        for i in results:
            if i is not None:
                self.add_to_inputs(i)

        print(f"Total inputs added...{len(self.inputs) - original_inputs}")
        self.write_inputs_file()
        # stop timer
        stop = time.perf_counter()
        #self.cleanup()

        print("Runner is Done.")
        print(f"Run Statistics:\nTime Taken: {stop-start} seconds")
        return stop-start, inputs_pre_deduplication, inputs_post_deduplication


if __name__ == "__main__":
    # oracle_program, function_name, survived_mutations, checker
    oracle_program_path = "working-directory-add_rm_ftz_sat_f32/add_rm_ftz_sat_f32_copy.c"
    function_name = "execute_add_rm_ftz_sat_f32"
    survived_mutations = "mutated-programs-add_rm_ftz_sat_f32"
    inputs = "test-dedup/data/f32_2.ssv"
    e = EquivalenceChecker(oracle_program_path, function_name, survived_mutations, inputs)
    try:
        e.runner()
        # print(EquivalenceChecker.bin_to_float("01001011000000000000000000000000"))
        # result = e.get_counterexample_from_CBMC("equivalence_check_add_rm_ftz_sat_f32.MUT2.c.c", "add_rm_ftz_sat_f32.MUT2.c")
        # print(result)
    except Exception as e:
        print(e)


