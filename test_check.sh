#!/bin/sh

TESTS="test_input/test[1-9]*.py"
# comment out to use python from path
#PYTHON="python2"
#PYTHON="$HOME/build/python/2_3/python"
#PYTHON="$PYTHON -tt coverage.py -x"
#PYTHON="/usr/bin/python2.3"

if [ "$PYTHON" = "" ]; then
    PYTHON=python
fi

if [ $# -gt 0 ]; then
    TESTS=""
    for arg in $* ; do
        TESTS="$TESTS test_input/test${arg}.py"
    done
fi

TMP=`mktemp -t -d tmp.pychecker.test_check.XXXXXXXXXX`

function get_expected ()
# Find a versioned expected output file
# Use the expected one with the highest version equal to or lower than
# our python version
# Fall back to the unversioned one
# arg1: test name
# sets EXPECTED
{
  local NAME=$1

  local VERSION=`$PYTHON -c "import sys ; print '%d.%d' % sys.version_info[0:2]"`

  # start with the unversioned one
  EXPECTED=test_expected/$NAME

  # FIXME: using \< and \> is not elegant, but python's versioning is
  # well-behaved
  ALL=`ls test_expected/$NAME-* 2> /dev/null`
  if test -z "$ALL"
  then
    return
  fi

  for CANDIDATE in $ALL
  do
    WANTED=test_expected/$NAME-$VERSION
    # echo candidate $CANDIDATE, with our version $WANTED
    if test ! $CANDIDATE \> $WANTED
    then
      # echo $CANDIDATE sorts before $WANTED
      if test $CANDIDATE \> $EXPECTED
      then
        # echo $CANDIDATE sorts after $EXPECTED, so new EXPECTED is $CANDIDATE
        EXPECTED=$CANDIDATE
      fi
    # else
      # echo $CANDIDATE sorts equal or after $WANTED
    fi
  done
  # echo EXPECTED: $EXPECTED
}


error=0

VERSION=`$PYTHON -c "import sys ; print '%d.%d' % sys.version_info[0:2]"`
FAILED=""
NO_EXPECTED_RESULTS=""
for test_file in $TESTS ; do
    echo "Testing $test_file ..."
    test_name=`basename $test_file .py`
    get_expected $test_name

    # make sure to use the -F option for this special test
    extra_args=""
    if [ "$test_file" = "test_input/test39.py" ]; then
        extra_args="-F test_input/pycheckrc"
    fi

    test_path=$TMP/$test_name
    $PYTHON -tt ./pychecker/checker.py --limit 0 --moduledoc --classdoc --no-argsused $extra_args $test_file 2>&1 | egrep -v '\[[0-9]+ refs\]$' > $test_path
    # mangle any system path-like paths that warning lines start with;
    # this allows us to compare to fixed expected output irrespective
    # of where python is installed, making it reproducable
    # FIXME: someone translate this to an equivalent line of python or sed
    perl -i -p -e 's@.*/lib(.*)/python\d.\d/@[system path]/@g' $test_path
    diff $test_path $EXPECTED
    if [ $? -ne 0 ]; then
        error=`expr $error + 1`
        echo "  $test_name FAILED; output different from expected in $EXPECTED"
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

rm -rf $TMP

exit $error
