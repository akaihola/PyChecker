#! /bin/sh
PYTHONPATH=$PYTHONPATH:.. pychecker *.py
echo ==============================================================
scripts/pychecker2.sh $* *.py
