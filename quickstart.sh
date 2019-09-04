#!/bin/bash
# -*- sh-basic-offset: 2; -*-
#
# Please format this file with shfmt from https://github.com/mvdan/sh/releases
# by running the following command:
#
# shfmt -i 2 -w quickstart.sh

set -e

# Variables
: "${DOCKER_IMAGE_NAME:=trustlines/quickstart:master}"
: "${DATA_DIR:=${PWD}/trustlines}"
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

The quickstart script needs Docker to be installed. The executable could not
been found. Please make sure it is available.

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

$ sudo goupadd docker
$ sudo usermod -a -G docker $USER

EOF
    exit 1
  fi
}

function run_quickstart_container() {
  # Update if refer to remote image.
  if [[ "$DOCKER_IMAGE_NAME" == *"/"* ]]; then
    printmsg <<EOF

Update the quickstart docker image...

EOF

    docker pull "$DOCKER_IMAGE_NAME"
  fi

  mkdir -p "$DATA_DIR"

  docker run --rm --tty --interactive \
    --volume /var/run/docker.sock:/var/run/docker.sock \
    --volume /usr/bin/docker:/usr/bin/docker \
    --volume "${PWD}":/data \
    --volume "$DATA_DIR":/quickstart/trustlines \
    $DOCKER_IMAGE_NAME \
    --host-base-dir "${PWD}"
}

function main() {
  sanityChecks
  run_quickstart_container
}

main
