#!/usr/bin/env python3
#
# This is a rip-off of parsl.configs.local_threads

from parsl.config import Config
from parsl.executors.threads import ThreadPoolExecutor
import os

if os.cpu_count() is None:
    config = Config(executors=[ThreadPoolExecutor()])
else:
    config = Config(executors=[ThreadPoolExecutor(max_threads=os.cpu_count())])
