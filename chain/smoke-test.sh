#!/usr/bin/env bash
# A simply smoke test for the blockchain image,
# that will just start the image and then checks if it has crashed after a wait time
# usage: smoke-test.sh <image tag>

error() {
  echo "Error: $*" 1>&2
}

EXIT_CODE=0

# Run in background and remember PID
docker run --rm --name testrun "$1" &
PID=$!

# Give it some time
sleep 20

if [ -z "$(ps -q $PID -o state --no-headers)" ]; then
  error "It seems like the blockchain image crashed"
  EXIT_CODE=1
else
  echo "Everything fine"
fi

docker stop testrun
exit $EXIT_CODE
