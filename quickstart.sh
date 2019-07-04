#!/bin/bash
# -*- sh-basic-offset: 2; -*-

set -e

# Variables
: "${DOCKER_IMAGE_PARITY:=trustlines/tlbc-testnet}"
DOCKER_IMAGE_WATCHTOWER="v2tec/watchtower"
: "${DOCKER_IMAGE_QUICKSTART:=trustlines/quickstart:master3734}"

DOCKER_CONTAINER_PARITY="trustlines-testnet"
DOCKER_CONTAINER_WATCHTOWER="watchtower-testnet"

PERMISSION_PREFIX=""
BASE_DIR=$(pwd)/trustlines
DATABASE_DIR=$BASE_DIR/database
CONFIG_DIR=$BASE_DIR/config
ENODE_DIR=$BASE_DIR/enode
PASSWORD_FILE=$CONFIG_DIR/pass.pwd
PASSWORD=""
ADDRESS_FILE=$CONFIG_DIR/address
ADDRESS=""


GREEN='\033[0;32m'
RESET='\033[0m'
function printmsg() {
  echo -en $GREEN
  cat
  echo -en $RESET
}

# Function for some checks at the beginning to make sure everything will run well.
# This includes the check for commands, permissions and the environment.
# The checks can close the process with an error message or set additional options.
#
function sanityChecks {
  # Check if Docker is ready to use.
  if ! command -v docker >/dev/null ; then
    printmsg <<EOF

ERROR

The quickstart script needs a working docker installation, but the
docker executable has not been found. Please install docker.

EOF
    exit 1
  fi

  # Check if user is part of the docker group.
  if [[ $(getent group docker) != *"$USER"* ]] ; then
    # Request the user for root permissions for specific commands.
    PERMISSION_PREFIX="sudo"
  fi
}

function readPassword {
  local PASSWORD2;
  while true; do
    read -s -p "Password: " PASSWORD
    echo
    if [ -z $PASSWORD ]; then
      echo "Password must not be empty.";
      continue
    fi
    read -s -p "Password (again): " PASSWORD2
    echo
    if [ "$PASSWORD" = "$PASSWORD2" ]; then
      return 0
    fi
    echo "Passwords do not match, please try again"
  done
}

function ensureCleanSetup() {
  if test -d "$CONFIG_DIR/keys"; then
    printmsg <<EOF
ERROR

The directory holding the keys already exists. This should not happen
during normal operations.

EOF
    exit 1
  fi

  if test -e $PASSWORD_FILE; then
    printmsg <<EOF
ERROR

The password file already exists. This should not happen during normal
operations.

EOF
    exit 1
  fi
}

function generateNewAccount() {
  printmsg <<EOF

This script will now generate a new validator private key. Please
enter a password. The password will be used to encrypt your validator
private key. The password will additionally be stored as plaintext in

  $PASSWORD_FILE

EOF

  readPassword

  ADDRESS=$(yes $PASSWORD | \
              $PERMISSION_PREFIX docker run \
                                 --interactive --rm \
                                 --volume $CONFIG_DIR:/config/custom \
                                 $DOCKER_IMAGE_PARITY \
                                 --parity-args account new |\
              grep -E -o "0x[0-9a-fA-F]{40}")
  storePassword
  storeAddress
}

function storePassword() {
  echo "$PASSWORD" > $PASSWORD_FILE
}

function storeAddress() {
  if test -z $ADDRESS; then
    cat <<EOF

ERROR

Could not determine address

EOF
    exit 1
  fi

  echo "$ADDRESS" > $ADDRESS_FILE
  printmsg <<EOF

Your validator address is $ADDRESS

EOF
}

function extractAddressFromKeyfile() {
  local address=$(grep -E -o '"address":[ \t]*"([a-zA-Z0-9]{40})"' $1 |grep -E -o '[a-zA-Z0-9]{40}')
  if test -n $address; then
     echo -n 0x$address
  fi
}

function importKeyfile() {
  local keyfile=$1
  ADDRESS=$(extractAddressFromKeyfile $keyfile)

  printmsg <<EOF

We will now import the keyfile from

  $keyfile

This keyfile contains the private key for the address

  $ADDRESS

Please enter a password. The password will be used to encrypt your
validator private key. The password will additionally be stored as
plaintext in

  $PASSWORD_FILE

Please enter the password for the keyfile.

EOF

  $PERMISSION_PREFIX docker run --rm -it \
                     --volume $CONFIG_DIR:/config/ \
                     --volume $keyfile:/tmp/account-key.json \
                     $DOCKER_IMAGE_QUICKSTART \
                     qs-import-keystore-file /config/pass.pwd /config/address /config/keys/Trustlines/account.json /tmp/account-key.json
}

function importPrivateKey() {
  # Pull and start the container
  $PERMISSION_PREFIX docker run --rm -it\
                     --volume $CONFIG_DIR:/config  \
                     $DOCKER_IMAGE_QUICKSTART \
                     qs-import-private-key /config/pass.pwd /config/address /config/keys/Trustlines/account.json
}

function askYesOrNo() {
  while true; do
    read -p "$1 ([y]es or [n]o): "
    case $(echo $REPLY | tr '[A-Z]' '[a-z]') in
      y|yes) echo "yes"; break ;;
      n|no) echo "no"; break;;
      *) continue ;;
    esac
  done
}

function setupAccountInteractive() {
  printmsg <<EOF

This script will setup a validator node for the trustlines test
chain. We will need to download some docker images. This will take
some time. Please be patient.

EOF

  pullDockerImages

  # Create directories.
  mkdir -p $DATABASE_DIR
  mkdir -p $CONFIG_DIR
  mkdir -p $ENODE_DIR

  printmsg <<EOF

A validator node will need a private key. This script can either
import an existing json keyfile, import an existing private key, or it
can create a new key.

EOF

  if [ $(askYesOrNo "Do you want to import an existing keyfile?") = "yes" ]; then
      local keyfile=$(pwd)/account-key.json
      if test -e $keyfile; then
        importKeyfile $keyfile
      else
        printmsg <<EOF

You have to copy an existing keyfile to the following location:

  $keyfile

If you have done that, please run this script again. It will
automatically import the account from this keyfile.

EOF
        exit 0
      fi
  elif [ $(askYesOrNo "Do you want to import an existing private key?") = "yes" ]; then
    importPrivateKey
  else
    generateNewAccount
  fi
}

function pullDockerImages() {
  for img in $DOCKER_IMAGE_PARITY $DOCKER_IMAGE_WATCHTOWER $DOCKER_IMAGE_QUICKSTART ; do
    case $img in
      */*)

        $PERMISSION_PREFIX docker pull $img
        ;;

      *) # do not pull local images used for testing
        echo "===> not pulling $img"
        ;;
      esac
  done
}


# Start the Watchtower within its Docker container.
# It checks if the container is already running and do nothing, is stopped and restart it or create a new one.
#
function startWatchtower {
  # Check if container is already running.
  if [[ $($PERMISSION_PREFIX docker ps) == *"$DOCKER_CONTAINER_WATCHTOWER"* ]] ; then
    printmsg <<EOF
The Watchtower client is already running as container, stopping it..."
EOF
    $PERMISSION_PREFIX docker stop $DOCKER_CONTAINER_WATCHTOWER
  fi
  # Check if the container does already exist and restart it.
  if [[ $($PERMISSION_PREFIX docker ps -a) == *"$DOCKER_CONTAINER_WATCHTOWER"* ]] ; then
    printmsg <<EOF
The Watchtower container already exists, deleting it..."
EOF
    $PERMISSION_PREFIX docker rm $DOCKER_CONTAINER_WATCHTOWER
  fi
  # Pull and start the container
  printmsg <<EOF
Starting the Watchtower client.
EOF
  $PERMISSION_PREFIX docker run \
    --detach \
    --name $DOCKER_CONTAINER_WATCHTOWER \
    --volume /var/run/docker.sock:/var/run/docker.sock \
    $DOCKER_IMAGE_WATCHTOWER
}


# Start of the validator Parity node within its Docker container.
# It checks if the container is already running and do nothing, is stopped and restart it or create a new one.
# This reads in the stored address first.
# The whole container setup plus arguments will be handled automatically.
#
function startNode {
  # Check if container is already running.
  if [[ $($PERMISSION_PREFIX docker ps) == *"$DOCKER_CONTAINER_PARITY"* ]] ; then
    printmsg <<EOF
The Parity client is already running as container with name '$DOCKER_CONTAINER_PARITY', stopping it...
EOF
    $PERMISSION_PREFIX docker stop $DOCKER_CONTAINER_PARITY
  fi

  # Check if the container does already exist and restart it.
  if [[ $($PERMISSION_PREFIX docker ps -a) == *"$DOCKER_CONTAINER_PARITY"* ]] ; then
    printmsg <<EOF
The Parity container already exists, deleting it...
EOF
    $PERMISSION_PREFIX docker rm $DOCKER_CONTAINER_PARITY
  fi


  # Create and start a new container.
  printmsg <<EOF

Start the Parity client as validator...

EOF

  ## Read in the stored address file.
  local address=$(cat $ADDRESS_FILE)

  ## Start Parity container with all necessary arguments.
  $PERMISSION_PREFIX docker run \
    --detach \
    --name $DOCKER_CONTAINER_PARITY \
    --volume $DATABASE_DIR:/data \
    --volume $CONFIG_DIR:/config/custom \
    --volume $ENODE_DIR:/config/network \
    -p 30300:30300 \
    -p 30300:30300/udp \
    --restart=on-failure \
    $DOCKER_IMAGE_PARITY \
    --role validator \
    --address $address

  printmsg <<EOF

Parity node as started and is running in background!

EOF
}



# Getting Started
sanityChecks

if test -e $ADDRESS_FILE; then
  printmsg <<EOF

You already have a setup for a validator node.

We will now update the docker images needed for the operation of a
validator node. This may take some time. Please be patient.

EOF
  pullDockerImages
else
  ensureCleanSetup
  setupAccountInteractive
fi

startWatchtower
startNode
