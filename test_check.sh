#!/bin/sh

TESTS="test_input/test[1-9]*.py"
# comment out to use python from path
# PYTHON="$HOME/local/bin/python2.2 -tt"
# PYTHON="$HOME/build/python/dist/src/python -tt"
# PYTHON="/usr/bin/python -tt"
PYTHON="/usr/bin/python2.1 -tt"
# PYTHON="$PYTHON coverage.py -x"

if [ $# -gt 0 ]; then
    TESTS=""
    for arg in $* ; do
        TESTS="$TESTS test_input/test${arg}.py"
    done
fi

if [ -z "$TMP" ]; then
    TMP=/tmp
fi

error=0

FAILED=""
NO_EXPECTED_RESULTS=""
for test_file in $TESTS ; do
    echo "Testing $test_file ..."
    test_name=`basename $test_file .py`
    expected=test_expected/$test_name
    if [ ! -e $expected ]; then
        echo "  WARNING:  $expected expected results does not exist"
	NO_EXPECTED_RESULTS="$NO_EXPECTED_RESULTS $test_name"
	continue
    fi

    test_path=$TMP/$test_name
    $PYTHON ./pychecker/checker.py --moduledoc --classdoc --no-argsused $test_file > $test_path 2>&1
    diff $test_path $expected
    if [ $? -ne 0 ]; then
    	error=`expr $error + 1`
	echo "  $test_name FAILED"
	FAILED="$FAILED $test_name"
    fi
    rm -f $test_path
done

if [ $error -ne 0 ]; then
    echo ""
    echo "$errors TESTS FAILED: $FAILED"
else
    echo "ALL TESTS PASSED"
fi

if [ "$NO_EXPECTED_RESULTS" != "" ]; then
    echo " WARNING no expected results for: $NO_EXPECTED_RESULTS"
fi

