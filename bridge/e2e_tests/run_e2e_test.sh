#! /bin/bash

set -e

DOCKER_COMPOSE_COMMAND="docker-compose -f ../docker-compose.yml -f docker-compose-override.yml"
E2E_DIRECTORY=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
BASE_DIRECTORY=$(realpath "$E2E_DIRECTORY/../../")
BRIDGE_DATA_DIRECTORY="$BASE_DIRECTORY/bridge/bridge_data"
CONTRACT_DIRECTORY="$BASE_DIRECTORY/contracts/contracts"
VALIDATOR_SET_CSV_FILE="$E2E_DIRECTORY/validator_list.csv"
ENVIRONMENT_VARIABLES_FILE="$E2E_DIRECTORY/env_override"
SIDE_CHAIN_SPEC_FILE="$E2E_DIRECTORY/node_config/side_chain_spec.json"
: "${VIRTUAL_ENV:=$BASE_DIRECTORY/venv}"
PREMINTED_TOKEN_AMOUNT="10000000000000000000000"
TRANSFER_TOKEN_AMOUNT="1000000000000000000"
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

# Enable for debug output
set -o functrace # run DEBUG trap in subshells
trap preexec DEBUG

function cleanup() {
  cwd=$(pwd)
  cd "$E2E_DIRECTORY"
  $DOCKER_COMPOSE_COMMAND down -v
  $DOCKER_COMPOSE_COMMAND rm -v
  cd "$cwd"
  # we need root rights to delete some of the files
  docker run -v "$BRIDGE_DATA_DIRECTORY":/data --rm ubuntu:18.04 bash -c 'rm -rf /data/*'
  rm -rf "$BRIDGE_DATA_DIRECTORY"
}

trap "cleanup" EXIT
trap "exit 1" SIGINT SIGTERM

# Execute a command and parse a possible hex address from the output.
# The address is expected to start with 0x.
# Only the last address will be returned.
#
# Arguments:
#   $1 - command to execute
#
function executeAndParseHexAddress() {
  output=$($1)
  parseLastHexAddress "$output"
}

function parseLastHexAddress {
  sanitizedString=${1//[$'\t\r\n']/ }
  hexAddressWithPostfix=${sanitizedString##*0x}
  echo "0x${hexAddressWithPostfix%% *}"
}

function parseFirstHexAddress {
  sanitizedString=${1//[$'\t\r\n']/ }
  hexAddressWithPostfix=${sanitizedString#*0x}
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
# pip install py-geth==2.1.0 'eth-tester[py-evm]==0.1.0-beta.39' pytest-ethereum==0.1.3a6 pysha3==1.0.2

echo "===> Start main and side chain node services"
$DOCKER_COMPOSE_COMMAND up --no-start
$DOCKER_COMPOSE_COMMAND up -d node_side node_main

echo "===> Wait for the chains to start up"
sleep 10

response=$(curl --silent --data \
  "{\"method\":\"eth_getBalance\",\"params\":[\"$VALIDATOR_ADDRESS\"],\"id\":1,\"jsonrpc\":\"2.0\"}" \
  -H "Content-Type: application/json" -X POST $NODE_SIDE_RPC_ADDRESS)
echo "Current Balance: $(convertHexToDecOfJsonRpcResponse \"$response\")"

echo "===> Deploy validator set proxy contract (with validator set)"
validator_set_proxy_contract_address=$(executeAndParseHexAddress "validator-set-deploy deploy-proxy \
  --jsonrpc $NODE_SIDE_RPC_ADDRESS --validators $VALIDATOR_SET_CSV_FILE")

echo "ValidatorSetProxy contract address: $validator_set_proxy_contract_address"

echo "===> Verify active validator set"
validator-set-deploy print-validators --jsonrpc "$NODE_SIDE_RPC_ADDRESS" --address "$validator_set_proxy_contract_address"

echo "===> Deploy foreign bridge contracts"

foreign_bridge_contract_address=$(executeAndParseHexAddress "bridge-deploy deploy-foreign \
  --jsonrpc $NODE_MAIN_RPC_ADDRESS")

echo "ForeignBridge contract address: $foreign_bridge_contract_address"

echo "===> Deploy home bridge validators contracts"

home_bridge_validators_contract_address=$(
  executeAndParseHexAddress \
    "bridge-deploy deploy-validators --jsonrpc $NODE_SIDE_RPC_ADDRESS \
    --validator-proxy-address $validator_set_proxy_contract_address \
    --required-signatures-multiplier 1 \
    --required-signatures-divisor 1"
)

echo "HomeBridgeValidators contract address: $home_bridge_validators_contract_address"

echo "===> Check required signatures"
deploy-tools call --jsonrpc $NODE_SIDE_RPC_ADDRESS --contracts-dir "$CONTRACT_DIRECTORY" \
  --contract-address $home_bridge_validators_contract_address BridgeValidators requiredSignatures

echo "===> Check isValidator"
deploy-tools call --jsonrpc $NODE_SIDE_RPC_ADDRESS --contracts-dir "$CONTRACT_DIRECTORY" \
  --contract-address $home_bridge_validators_contract_address BridgeValidators isValidator \
  $VALIDATOR_ADDRESS

echo "===> Deploy home bridge contracts"

# Use block reward of 0 wei to be able comparing the validators balance for the
# later bridge transfer. Before the reward contract, this is already zero.
deploy_home_result=$(bridge-deploy deploy-home --jsonrpc $NODE_SIDE_RPC_ADDRESS \
--bridge-validators-address $home_bridge_validators_contract_address \
--required-block-confirmations 1 \
--owner-address $VALIDATOR_ADDRESS \
--block-reward-amount 0 \
--gas 7000000 \
--gas-price 10)

block_reward_contract_address=$(parseFirstHexAddress "$deploy_home_result")
home_bridge_contract_address=$(parseLastHexAddress "$deploy_home_result")

echo "BlockReward contract address: $block_reward_contract_address"
echo "HomeBridge contract address: $home_bridge_contract_address"

echo "===> Deploy token contract"

token_contract_address=$(
  executeAndParseHexAddress "deploy-tools deploy \
  --jsonrpc $NODE_MAIN_RPC_ADDRESS --contracts-dir $CONTRACT_DIRECTORY \
  TrustlinesNetworkToken TrustlinesNetworkToken TNC 18 $VALIDATOR_ADDRESS $PREMINTED_TOKEN_AMOUNT"
)

echo "Token contract address: $token_contract_address"

echo "===> Check token balance"

deploy-tools call --jsonrpc $NODE_MAIN_RPC_ADDRESS --contracts-dir "$CONTRACT_DIRECTORY" \
  --contract-address "$token_contract_address" TrustlinesNetworkToken \
  balanceOf $VALIDATOR_ADDRESS

echo "===> Get side chain block number"

response=$(curl --silent --data \
  '{"method":"eth_blockNumber","params":[],"id":1,"jsonrpc":"2.0"}' \
  -H "Content-Type: application/json" -X POST $NODE_SIDE_RPC_ADDRESS)
current_block_number=$(convertHexToDecOfJsonRpcResponse "$response")

block_reward_contract_transition_block=$((current_block_number + 20))

echo "Current block number: $current_block_number"
echo "BlockReward contract transition block: $block_reward_contract_transition_block"

echo "===> Stop main and side chain node services"
$DOCKER_COMPOSE_COMMAND stop node_side node_main

echo "===> Set bridge environment variables"

# Even if this does not change as long as the address and order of deployment isn't touched,
# this makes sure the environment is set up 100% correctly.
sed -i "s/\(FOREIGN_BRIDGE_ADDRESS=\).*/\1$foreign_bridge_contract_address/" "$ENVIRONMENT_VARIABLES_FILE"
sed -i "s/\(HOME_BRIDGE_ADDRESS=\).*/\1$home_bridge_contract_address/" "$ENVIRONMENT_VARIABLES_FILE"
sed -i "s/\(ERC20_TOKEN_ADDRESS=\).*/\1$token_contract_address/" "$ENVIRONMENT_VARIABLES_FILE"

echo "===> Set BlockReward contract address and transition block"

sed -i '/blockRewardContractAddress/c\                \"blockRewardContractAddress\": \"'"$block_reward_contract_address"'\",' "$SIDE_CHAIN_SPEC_FILE"
sed -i '/blockRewardContractTransition/c\                \"blockRewardContractTransition\": '"$block_reward_contract_transition_block"'' "$SIDE_CHAIN_SPEC_FILE"

echo "===> Start main and side chain node services"
$DOCKER_COMPOSE_COMMAND start node_side node_main

echo "===> Wait for the chains to start up"
sleep 10

echo "===> Wait until block reward contract transition"

while [[ $current_block_number -lt $((block_reward_contract_transition_block + 5)) ]]; do
  printf .
  response=$(curl --silent --data \
    '{"method":"eth_blockNumber","params":[],"id":1,"jsonrpc":"2.0"}' \
    -H "Content-Type: application/json" -X POST $NODE_SIDE_RPC_ADDRESS)
  current_block_number=$(convertHexToDecOfJsonRpcResponse "$response")
  sleep 1
done

printf '\n'

echo "Current block number: $current_block_number"

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

# Wait some more
sleep 5
printf '.\n'

echo "===> Test a bridge transfer from foreign to home chain"

# Check balance before
response=$(curl --silent --data \
  "{\"method\":\"eth_getBalance\",\"params\":[\"$VALIDATOR_ADDRESS\"],\"id\":1,\"jsonrpc\":\"2.0\"}" \
  -H "Content-Type: application/json" -X POST $NODE_SIDE_RPC_ADDRESS)
homeNativeBalanceBefore=$(convertHexToDecOfJsonRpcResponse "$response")
echo "Balance on home chain before: $homeNativeBalanceBefore"


echo "===> Transfer token to foreign bridge"

deploy-tools transact --jsonrpc $NODE_MAIN_RPC_ADDRESS --contracts-dir "$CONTRACT_DIRECTORY" \
  --contract-address "$token_contract_address" TrustlinesNetworkToken transfer \
  "$foreign_bridge_contract_address" $TRANSFER_TOKEN_AMOUNT \
  --gas 7000000 \
  --gas-price 10

echo "===> Check token balance"

deploy-tools call --jsonrpc $NODE_MAIN_RPC_ADDRESS --contracts-dir "$CONTRACT_DIRECTORY" \
  --contract-address "$token_contract_address" TrustlinesNetworkToken \
  balanceOf $VALIDATOR_ADDRESS

echo "===> Wait for transfer to finish"
bridgeSenderLog=''
while [[ $bridgeSenderLog != *"Finished processing msg"* ]]; do
  printf .
  bridgeSenderLog=$($DOCKER_COMPOSE_COMMAND logs --tail 20 bridge_senderhome)
  sleep 5
done

sleep 10

echo "===> RewardContract Stats"

echo "blockRewardAmount: $(deploy-tools call --jsonrpc $NODE_SIDE_RPC_ADDRESS --contracts-dir "$CONTRACT_DIRECTORY" \
  --contract-address $block_reward_contract_address RewardByBlock blockRewardAmount)"

echo "mintedForAccount: $(deploy-tools call --jsonrpc $NODE_SIDE_RPC_ADDRESS --contracts-dir "$CONTRACT_DIRECTORY" \
  --contract-address $block_reward_contract_address RewardByBlock mintedForAccount $VALIDATOR_ADDRESS)"

echo "mintedTotally: $(deploy-tools call --jsonrpc $NODE_SIDE_RPC_ADDRESS --contracts-dir "$CONTRACT_DIRECTORY" \
  --contract-address $block_reward_contract_address RewardByBlock mintedTotally)"


response=$(curl --silent --data \
  "{\"method\":\"eth_getBalance\",\"params\":[\"$VALIDATOR_ADDRESS\"],\"id\":1,\"jsonrpc\":\"2.0\"}" \
  -H "Content-Type: application/json" -X POST $NODE_SIDE_RPC_ADDRESS)
homeNativeBalanceAfter=$(convertHexToDecOfJsonRpcResponse "$response")
echo "Balance on home chain after: $homeNativeBalanceAfter"


if [[ $homeNativeBalanceAfter -le $homeNativeBalanceBefore ]]; then
  echo "Balance has not increased by transfer!"
  exit 1
fi

echo "===> Shutting down"
exit 0
