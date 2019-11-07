#!/usr/bin/env bash
# A simply smoke test for the blockchain image,
# that will just start the image and then checks if it has crashed after a wait time
# usage: smoke-test.sh <image tag>

error() {
  echo "Error: $*" 1>&2
}

EXIT_CODE=0

# Start container with some arbitrary options to also test option parsing to parity
docker run -d --name testrun "$1" --parity-args --no-color

# Give it some time
sleep 20
# Show logs
docker logs testrun

if [ -z "$(docker ps -q -f name=testrun)" ]; then
  # Check if the container is still running
  error "It seems like the blockchain image crashed"
  EXIT_CODE=1
else
  echo "Everything fine"
fi

# Clean up
docker stop testrun
docker rm testrun
exit $EXIT_CODE
