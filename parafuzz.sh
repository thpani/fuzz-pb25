#!/bin/bash

seq 0 9 | parallel './pbfuzz.py > {}.log'

# To halt on the first failure and not continue with the rest of the jobs, you can use:
# seq 0 9 | parallel --halt now,fail=1 './pbfuzz.py > {}.log'
