#! /bin/sh
NAME=`dirname $0`
NAME=`dirname $NAME`/..
PYTHONPATH=$NAME:$PYTHONPATH export PYTHONPATH
CHECKER='python2.2 $NAME/pychecker2/main.py'

if [ "$1" = "generate" ]
then
    OUTPUT=' &> '
else
    OUTPUT=' 2>&1 | diff - '
fi

2>&1

eval $CHECKER tests/*.py $OUTPUT tests/expected/normal  
eval $CHECKER -?         $OUTPUT tests/expected/options 

for opt in verbose shadowBuiltins reportUnusedSelf
do
   eval $CHECKER --${opt} tests/*.py $OUTPUT tests/expected/$opt
done



