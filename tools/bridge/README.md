Trustlines Bridge Validator
===========================

Building
--------
The docker container needs to be built from the root path, so

```bash
docker build --file ./Dockerfile ../../
```

Development
-----------
### Start the development/testnet light nodes
```bash
docker-compose --project-name tlbc-bridge -f ./docker/docker-compose-nodes-development.yml up
```

### Run the application locally

```bash
make start
```

#### Local configuration
You can overwrite the .env parameters with predefined environment variables, so you can have your .env point to the docker hosts while locally using
```bash
HOME_RPC_URL=http://localhost:8546 FOREIGN_RPC_URL=http://localhost:8545 make start
```

### **or** start the Docker file

```bash
docker-compose --project-name tlbc-bridge -f ./docker/docker-compose.yml build
docker-compose --project-name tlbc-bridge -f ./docker/docker-compose.yml up
```

Production
----------
### Start Nodes & Service
```bash
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose.yml --file ./docker/docker-compose-nodes-production.yml build
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose.yml --file ./docker/docker-compose-nodes-production.yml up --detach
```

### View Logs
```bash
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose.yml --file ./docker/docker-compose-nodes-production.yml logs --tail 200 -f
```

### Stop Nodes & Service
```bash
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose.yml --file ./docker/docker-compose-nodes-production.yml down
```

**There is no production Trustlines chain yet, so this won't work**
