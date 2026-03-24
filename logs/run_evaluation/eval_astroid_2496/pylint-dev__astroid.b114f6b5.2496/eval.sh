#!/bin/bash
set -uxo pipefail
cd /testbed
: '>>>>> Start Test Output'
source /opt/miniconda3/bin/activate; conda activate testbed; pytest --disable-warnings --color=no --tb=no --verbose
: '>>>>> End Test Output'
