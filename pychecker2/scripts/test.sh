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

for opt in verbose shadowBuiltins reportUnusedSelf \
    no-operator no-operatorPlus no-redefinedScope no-shadowIdentifier \
    no-syntaxErrors no-unknown no-unused 
do
   echo $opt
   eval $CHECKER --${opt} tests/*.py tests/not_there.py $OUTPUT tests/expected/$opt
done



