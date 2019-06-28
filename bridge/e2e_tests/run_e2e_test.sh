#! /bin/bash

set -e

E2E_DIRECTORY=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
BRIDGE_DATA_DIRECTORY=$(realpath "$E2E_DIRECTORY/../bridge_data")
DOCKER_COMPOSE_COMMAND="docker-compose -f ../docker-compose.yml -f docker-compose-override.yml"

# The following variables must be known within the bridge containers.
set -a
VALIDATOR_ADDRESS=0x46ae357ba2f459cb04697837397ec90b47e48727
VALIDATOR_ADDRESS_PRIVATE_KEY=a17b8b084a4019298e48c6f8fb84d92e35be9ae22142f0472b8fe43ad6de5d22
set +a

OPTIND=1
ARGUMENT_DOCKER_BUILD=0
ARGUMENT_DOCKER_PULL=0
ARGUMENT_SILENT=0

while getopts "pbs" opt; do
  case "$opt" in
  b)
    ARGUMENT_DOCKER_BUILD=1
    ;;
  p)
    ARGUMENT_DOCKER_PULL=1
    ;;
  s)
    ARGUMENT_SILENT=1
    ;;
  *) ;;

  esac
done

# Optimized version of 'set -x'
function preexec() {
  if [[ $BASH_COMMAND != echo* ]] && [[ $ARGUMENT_SILENT -eq 0 ]]; then echo >&2 "+ $BASH_COMMAND"; fi
}

set -o functrace # run DEBUG trap in subshells
trap preexec DEBUG

function cleanup() {
  cwd=$(pwd)
  cd "$E2E_DIRECTORY"
  $DOCKER_COMPOSE_COMMAND down -v
  $DOCKER_COMPOSE_COMMAND rm -v
  cd "$cwd"
  rm -rf "$BRIDGE_DATA_DIRECTORY" # TODO: directory is permissioned (why?)
}

trap "cleanup" EXIT
trap "exit 1" SIGINT SIGTERM

if [[ $ARGUMENT_DOCKER_BUILD == 1 ]]; then
  echo "===> Build images for services"
  $DOCKER_COMPOSE_COMMAND build
fi

if [[ $ARGUMENT_DOCKER_PULL == 1 ]]; then
  echo "===> Pull images for services"
  $DOCKER_COMPOSE_COMMAND pull
fi

echo "===> Cleanup from previous runs"
cleanup

echo "===> Start main and side chain node services"
$DOCKER_COMPOSE_COMMAND up --no-start
$DOCKER_COMPOSE_COMMAND up -d node_side node_main

echo "===> Wait for the chains to start up"
sleep 10

echo "===> Start bridge services"

$DOCKER_COMPOSE_COMMAND up -d \
  rabbit redis bridge_request bridge_collected bridge_affirmation bridge_senderhome bridge_senderforeign

printf "===> Wait until message broker is up"

rabbit_log_length=0

# Mind the "Attaching to..." line at the beginning.
while [[ $rabbit_log_length -lt 2 ]]; do
  printf .
  rabbit_log=$($DOCKER_COMPOSE_COMMAND logs rabbit)
  rabbit_log_length=$(wc -l <<<"$rabbit_log")
  sleep 5
done

printf '\n'

echo "===> Shutting down"
exit 0
