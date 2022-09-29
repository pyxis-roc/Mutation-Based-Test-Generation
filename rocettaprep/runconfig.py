#!/usr/bin/env python3
#
# This is a rip-off of parsl.configs.local_threads

from parsl.config import Config
from parsl.executors.threads import ThreadPoolExecutor

from parsl.providers import LocalProvider
from parsl.channels import LocalChannel
from parsl.executors import HighThroughputExecutor

import os

if os.cpu_count() is None:
    config = Config(executors=[ThreadPoolExecutor()])

    htconfig = Config(
        executors=[
            HighThroughputExecutor(
                worker_debug=True,
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
    config = Config(executors=[ThreadPoolExecutor(max_threads=os.cpu_count())])

    htconfig = Config(
        executors=[
            HighThroughputExecutor(
                worker_debug=True,
                cores_per_worker=1,
                provider=LocalProvider(
                    channel=LocalChannel(),
                    init_blocks=1,
                    max_blocks=os.cpu_count(),
                ),
            )
        ],
        strategy=None
    )


