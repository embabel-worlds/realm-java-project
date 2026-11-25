#!/bin/sh
# Ground-truth battery for realm-java-project, over one public Maven project pinned at a commit
# (spring-projects/spring-petclinic, see PROJECT in verify.py).
#   L1 every view answers by name, on its defaults and the pinned project
#   L2 figures reconciled to the repository read directly (git clone at the same commit): files by
#      extension and source set, packages and their files, imports, annotations, settings keys,
#      the module's coordinates and the dependencies its POM declares
#   L3 none: this realm declares no pushdown of its own; the source-tree and maven kinds filter as they read
#
#   APPLIANCE=http://127.0.0.1:8080 AUTH=user:pass sh tests/verify.sh
# (EMBABEL_AUTH=user:pass is accepted in place of AUTH.) Needs git and python3 with PyYAML on the host.
# The last line on success is exactly `ALL CHECKS PASS`; any failure exits non-zero.
set -e
cd "$(dirname "$0")/.."
exec python3 tests/verify.py "$@"
