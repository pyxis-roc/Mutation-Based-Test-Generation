#!/usr/bin/env python3
#
# This is a rip-off of parsl.configs.local_threads

from parsl.config import Config
from parsl.executors.threads import ThreadPoolExecutor

from parsl.providers import LocalProvider
from parsl.channels import LocalChannel
from parsl.executors import HighThroughputExecutor

import os

# set to true when developing
wd = False
cc = os.cpu_count()

if cc is None:
    config = Config(executors=[ThreadPoolExecutor()])

    htconfig = Config(
        executors=[
            HighThroughputExecutor(
                worker_debug=wd,
                cores_per_worker=1,
                provider=LocalProvider(
                    channel=LocalChannel(),
                    init_blocks=1,
                    max_blocks=1,
                ),
            )
        ],
        strategy=None
        )
else:
    config = Config(executors=[ThreadPoolExecutor(max_threads=cc)])

    htconfig = Config(
        executors=[
            HighThroughputExecutor(
                worker_debug=wd,
                cores_per_worker=1,
                provider=LocalProvider(
                    channel=LocalChannel(),
                    init_blocks=1,
                    max_blocks=cc,
                ),
            )
        ],
        strategy=None
    )


