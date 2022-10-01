#!/usr/bin/env python3

import json

def write_inputgen(exptdir, subset, source, experiment, insn, totalgen, unique):
    with open(exptdir / f"inputgen.{subset}{experiment}.json", "w") as f:
        json.dump({'experiment': experiment,
                   'instruction': insn.insn,
                   'source': f'{subset}{source}', # unlike testcases.json, this does not include experiment because it flows into a table
                   'total': totalgen,
                   'unique': unique}, fp=f)

def add_testcases(workdir, subset, source, experiment, ntests, inpfile, outfile):
    with open(workdir / "testcases.json", "r") as f:
        testcases = json.load(fp=f)

    srcname = f'{subset}{source}.{experiment}'

    # delete previous entry
    testcases['tests'] = list([t for t in testcases['tests'] if t['source'] != srcname])

    if ntests > 0:
        testcases['tests'].append({'input': str(inpfile),
                                   'output': str(outfile),
                                   'source': srcname})

    with open(workdir / "testcases.json", "w") as f:
        json.dump(testcases, fp=f, indent='  ')

    return testcases

