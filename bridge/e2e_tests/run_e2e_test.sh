echo "===> Starting services"
VALIDATOR_ADDRESS=0x7e5f4552091a69125d5dfcb7b8c2659029395bdf VALIDATOR_ADDRESS_PRIVATE_KEY=0x0000000000000000000000000000000000000000000000000000000000000001 docker-compose -f ../docker-compose.yml -f docker-compose-override.yml up -d

echo "===> Testing nothing"
RABBIT_RUNNING=$(docker inspect -f '{{.State.Running}}' bridge_rabbit_1)
REDIS_RUNNING=$(docker inspect -f '{{.State.Running}}' bridge_redis_1)
REQUEST_RUNNING=$(docker inspect -f '{{.State.Running}}' bridge_bridge_request_1)
AFFIRMATION_RUNNING=$(docker inspect -f '{{.State.Running}}' bridge_bridge_affirmation_1)
SENDER_FOREIGN_RUNNING=$(docker inspect -f '{{.State.Running}}' bridge_bridge_senderforeign)
SENDER_HOME_RUNNING=$(docker inspect -f '{{.State.Running}}' bridge_bridge_senderhome_1)
COLLECTED_RUNNING=$(docker inspect -f '{{.State.Running}}' bridge_bridge_collected_1)

if [ "${RABBIT_RUNNING}" != "true" ] &&  \
   [ "${REDIS_RUNNING}" != "true" ] && \
   [ "${REQUEST_RUNNING}" != "true" ] && \
   [ "${AFFIRMATION_RUNNING}" != "true" ] && \
   [ "${SENDER_FOREIGN_RUNNING}" != "true" ] && \
   [ "${SENDER_HOME_RUNNING}" != "true" ] && \
   [ "${COLLECTED_RUNNING}" != "true" ]; then
  FAILED=1
else
  FAILED=0
fi

echo "===> Shutting down"
docker-compose -f ../docker-compose.yml -f docker-compose-override.yml down

exit $FAILED
