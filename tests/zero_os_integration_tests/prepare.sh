#!/bin/bash

function usage()
{
    echo "usage:"
    echo "   -h: listing  usage"
    echo "   -d: install requirements"
    echo "   -r: provide path for tests you want to run"
    echo ""
}

while getopts r:dh OPT
do
    case "$OPT" in
        h) usage
           exit;;
        d) DEP=True ;;
        r) TESTSPATH=$OPTARG ;;
    esac
done

## Cloning the framework
git -C /tmp clone -b master https://github.com/0-complexity/G8_testing.git
cp -r /tmp/G8_testing/functional_testing/zrobot_templates/framework .
rm -rf /tmp/G8_testing

## Install requirements
if [ ${DEP} ]; then
  echo " "
  echo "* Installing requirements"
  pip3 install -r requirements.txt
fi

## running testsuite
if [ ${TESTSPATH} ]; then
  echo " "
  echo "* Running Tests"
  nosetests -v -s ${TESTSPATH} --tc-file=config.ini
fi
