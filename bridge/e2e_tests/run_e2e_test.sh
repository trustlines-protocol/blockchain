#! /bin/bash

set -e

DOCKER_COMPOSE_COMMAND="docker-compose -f ../docker-compose.yml -f docker-compose-override.yml"
E2E_DIRECTORY=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
BASE_DIRECTORY=$(realpath "$E2E_DIRECTORY/../../")
BRIDGE_DATA_DIRECTORY="$BASE_DIRECTORY/bridge/bridge_data"
CONTRACT_DIRECTORY="$BASE_DIRECTORY/contracts/contracts"
VALIDATOR_SET_CSV_FILE="$E2E_DIRECTORY/validator_list.csv"
ENVIRONMENT_VARIABLES_FILE="$E2E_DIRECTORY/env_override"
VIRTUAL_ENV="$BASE_DIRECTORY/venv"
PREMINTED_TOKEN_AMOUNT=1
BLOCK_REWARD_CONTRACT_TRANSITION_BLOCK=70
NODE_SIDE_RPC_ADDRESS="http://127.0.0.1:8545"
NODE_MAIN_RPC_ADDRESS="http://127.0.0.1:8544"

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

# Execute a command and parse a possible hex address from the output.
# The address is expected to start with 0x.
# Only the first address will be returned.
#
# Arguments:
#   $1 - command to execute
#
function executeAndParseHexAddress() {
  output=$($1)
  hexAddressWithPostfix=${output##*0x}
  echo "0x${hexAddressWithPostfix%% *}"
}

function convertHexToDecOfJsonRpcResponse() {
  hexResult=$(echo "$1" | awk -F '0x' '{print $2}' | awk -F '"' '{print $1}')
  decResult=$((16#$hexResult))
  echo $decResult
}

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

echo "===> Prepare deployment tools"
(cd "$BASE_DIRECTORY" && make install-tools/validator-set-deploy)
(cd "$BASE_DIRECTORY" && make install-tools/bridge-deploy)
source "$VIRTUAL_ENV/bin/activate"
# TOOD: remove in future:
pip install py-geth==2.1.0 'eth-tester[py-evm]==0.1.0-beta.39' pytest-ethereum==0.1.3a6 pysha3==1.0.2

echo "===> Start main and side chain node services"
$DOCKER_COMPOSE_COMMAND up --no-start
$DOCKER_COMPOSE_COMMAND up -d node_side node_main

echo "===> Wait for the chains to start up"
sleep 10

echo "===> Deploy validator set contracts"
validator-set-deploy deploy --jsonrpc "$NODE_SIDE_RPC_ADDRESS" --validators "$VALIDATOR_SET_CSV_FILE"
validator_set_proxy_contract_address=$(executeAndParseHexAddress "validator-set-deploy deploy-proxy \
  --jsonrpc $NODE_SIDE_RPC_ADDRESS --validators $VALIDATOR_SET_CSV_FILE")

echo "ValidatorSetProxy contract address: $validator_set_proxy_contract_address"

echo "===> Deploy bridge contracts"

foreign_bridge_contract_address=$(executeAndParseHexAddress "bridge-deploy deploy-foreign \
  --jsonrpc $NODE_MAIN_RPC_ADDRESS")

echo "ForeignBridge contract address: $foreign_bridge_contract_address"

home_bridge_valdiators_address=$(
  executeAndParseHexAddress \
    "bridge-deploy deploy-validators --jsonrpc $NODE_SIDE_RPC_ADDRESS \
  --validator-proxy-address $validator_set_proxy_contract_address"
)

# TODO correct parsing of this stuff (does include reward contract as well now).

# Use block reward by zero to be able comparing the validators balance for the
# later bridge transfer. Before the reward contract, this is already zero.
home_bridge_contract_address=$(
  executeAndParseHexAddress \
    "bridge-deploy deploy-home --jsonrpc $NODE_SIDE_RPC_ADDRESS \
  --bridge-validators-address $home_bridge_valdiators_address \
  --required-block-confirmations 1 \
  --owner-address $VALIDATOR_ADDRESS \
  --block-reward-amount 0 \
  --gas 7000000 \
  --gas-price 10"
)

echo "HomeBridge contract address: $home_bridge_contract_address"

echo "===> Deploy token contract"
token_contract_address=$(
  executeAndParseHexAddress "deploy-tools deploy \
  --jsonrpc $NODE_MAIN_RPC_ADDRESS --contracts-dir $CONTRACT_DIRECTORY \
  TrustlinesNetworkToken TrustlinesNetworkToken TNC 18 $VALIDATOR_ADDRESS $PREMINTED_TOKEN_AMOUNT"
)

echo "Token contract address: $token_contract_address"

echo "===> Set bridge environment variables"

# Even if this does not change as long as the address and order of deployment isn't touched,
# this makes sure the environment is set up 100% correctly.
sed -i "s/\(FOREIGN_BRIDGE_ADDRESS=\).*/\1$foreign_bridge_contract_address/" "$ENVIRONMENT_VARIABLES_FILE"
sed -i "s/\(HOME_BRIDGE_ADDRESS=\).*/\1$home_bridge_contract_address/" "$ENVIRONMENT_VARIABLES_FILE"
sed -i "s/\(ERC20_TOKEN_ADDRESS=\).*/\1$token_contract_address/" "$ENVIRONMENT_VARIABLES_FILE"

printf "===> Wait until block reward contract transition"

blockNumber=0

while [[ $blockNumber -lt $BLOCK_REWARD_CONTRACT_TRANSITION_BLOCK ]]; do
  printf .
  response=$(curl --silent --data \
    '{"method":"eth_blockNumber","params":[],"id":1,"jsonrpc":"2.0"}' \
    -H "Content-Type: application/json" -X POST $NODE_SIDE_RPC_ADDRESS)
  blockNumber=$(convertHexToDecOfJsonRpcResponse "$response")
  sleep 1
done

printf '\n'

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
