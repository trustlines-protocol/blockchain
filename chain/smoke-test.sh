#!/usr/bin/env bash
# A simply smoke test for the blockchain image,
# that will just start the image and then checks if it has crashed after a wait time
# usage: smoke-test.sh <image tag>

error() {
  echo "Error: $*" 1>&2
}

EXIT_CODE=0

# Start container with some arbitrary options to also test option parsing to openethereum
docker run -d --name testrun "$1" --client-args --no-color

# Give it some time
sleep 10
# Show logs
docker logs testrun

if [ -z "$(docker ps -q -f name=testrun)" ]; then
  # Check if the container is still running
  error "It seems like the blockchain image crashed"
  EXIT_CODE=1
else
  echo "Image is running"
fi

if [ $EXIT_CODE -eq 0 ]; then
  # give it more time
  sleep 30

  # Show logs
  docker logs testrun

  # Check if importing blocks
  if ! docker logs testrun 2>&1 | grep -E "(Imported|Syncing) #[0-9]*"; then
    error "It seems like the image is not importing blocks"
    EXIT_CODE=2
  else
    echo "Image is importing block"
  fi

  # Check if can connect to boot nodes
  if ! docker logs testrun 2>&1 | grep "[3-9][0-9]*/[0-9]* peers"; then
    error "It seems like the image could not connected to at least all three bootnodes"
    EXIT_CODE=2
  else
    echo "Image was connected to at least all bootnodes"
  fi

  # Check if disconnected
  if docker logs testrun 2>&1 | grep "0/[0-9]* peers"; then
    error "It seems like the image was disconnected from all nodes"
    EXIT_CODE=2
  else
    echo "Image is still connected to nodes"
  fi

fi

# Clean up
docker stop testrun
docker rm testrun
exit $EXIT_CODE
