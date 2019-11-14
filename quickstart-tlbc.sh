#!/bin/bash
# -*- sh-basic-offset: 2; -*-
#
# Please format this file with shfmt from https://github.com/mvdan/sh/releases
# by running the following command:
#
# shfmt -i 2 -w quickstart-tlbc.sh

set -e

# Variables
: "${DOCKER_IMAGE:=trustlines/quickstart@sha256:99cd2ba2013c41a52687c42b132af5730c900aa39a93579bef6a2ea41f19c526}"
: "${DATA_DIR:=${PWD}/tlbc}"
GREEN='\033[0;32m'
RESET='\033[0m'

# Print colored messages to the user.
#
function printmsg() {
  echo -en "${GREEN}"
  cat
  echo -en "${RESET}"
}

# Function for some checks at the beginning to make sure everything will run well.
# This includes the check for commands, permissions and the environment.
# The checks can close the process with an error message or set additional options.
#
function sanityChecks() {
  if ! command -v docker >/dev/null; then
    printmsg <<EOF

ERROR

The quickstart script needs Docker to be installed. The executable
could not be found. Please make sure it is available.

EOF
    exit 1
  fi

  # Check if user is part of the docker group.
  if [[ $(getent group docker) != *"${USER}"* ]] && [[ "$USER" != "root" ]]; then
    printmsg <<EOF

ERROR

The quickstart script needs to be executable by a user from the 'docker' group
or as user 'root'. Please rerun the script as such.

Hint:
You can create the group 'docker' and add your current user with the following
commands.

$ sudo groupadd docker
$ sudo usermod -a -G docker $USER

EOF
    exit 1
  fi
}

function run_quickstart_container() {
  mkdir -p "$DATA_DIR"

  docker run --rm --tty --interactive \
    --volume /var/run/docker.sock:/var/run/docker.sock \
    --volume "${PWD}":/data \
    --volume "$DATA_DIR":/quickstart/tlbc \
    $DOCKER_IMAGE \
    "tlbc" \
    --host-base-dir "$DATA_DIR"
}

function main() {
  sanityChecks
  run_quickstart_container
}

main
