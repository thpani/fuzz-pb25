#!/bin/bash

seq 0 9 | parallel './pbfuzz.py > {}.log'
