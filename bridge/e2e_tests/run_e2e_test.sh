echo "===> Starting services"
VALIDATOR_ADDRESS=0x7e5f4552091a69125d5dfcb7b8c2659029395bdf VALIDATOR_ADDRESS_PRIVATE_KEY=0x0000000000000000000000000000000000000000000000000000000000000001 docker-compose -f ../docker-compose.yml -f docker-compose-override.yml up -d

echo "===> Testing nothing"

echo "===> Shutting down"
docker-compose -f ../docker-compose.yml -f docker-compose-override.yml down
