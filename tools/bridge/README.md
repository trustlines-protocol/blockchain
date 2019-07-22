Trustlines Bridge Validator
===========================

Building
--------
The docker container needs to be built from the root path, so

```bash
docker build --file ./Dockerfile ../../
```

Running
-------

Just mix & match all the components you want to run. Redis is not required currently.

### Start Development Stack
```bash
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose.yml --file ./docker/docker-compose-nodes-development.yml --file ./docker/docker-compose-redis.yml up --detach
```

### View Logs
```bash
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose.yml --file ./docker/docker-compose-nodes-development.yml --file ./docker/docker-compose-redis.yml logs -f
```

### Stop Development Stack
```bash
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose.yml --file ./docker/docker-compose-nodes-development.yml --file ./docker/docker-compose-redis.yml down
```

Production
----------
For the production stack, just replace the development nodes compose file with the production one.

**There is no production Trustlines chain yet, so this won't work**
