# This will build a docker image suitable for the Laika Testnet
#
# You can build the image from the parent dir with this command:
#
#   docker build -f laika/Dockerfile -t tlbc-testnet-next .

FROM ubuntu:18.04@sha256:f08638ec7ddc90065187e7eabdfac3c96e5ff0f6b2f1762cf31a4f49b53000a5

## Environment
ENV HOME=/home/openethereum
ENV NODE_HOME_DIR=$HOME/.local/share/openethereum
ENV CHAIN_SPEC_FILE=$NODE_HOME_DIR/trustlines-spec.json
ENV NODE_DATA_DIR=$NODE_HOME_DIR/chains
ENV NODE_DATABASE_DIR=$NODE_DATA_DIR/Trustlines/db
ENV CLIENT_BIN=/usr/local/bin/openethereum
ENV CLIENT_WRAPPER_SCRIPT=$HOME/client_wrapper.sh
ENV OPENETHERUEM_ZIP=/usr/local/openethereum.zip
ENV MIGRATION_TOOL_ZIP=/usr/local/migration.zip

RUN mkdir -p $NODE_HOME_DIR && \
    ls -la $NODE_HOME_DIR


# Donload unzip, cargo and clang (to run db migration tool)
RUN  apt-get update -y && \
     apt-get upgrade -y && \
     apt-get dist-upgrade -y && \
     apt-get -y autoremove && \
     apt-get clean
RUN apt-get install -y unzip cargo clang

# Download openethereum
ADD https://github.com/openethereum/openethereum/releases/download/v3.1.0/openethereum-linux-v3.1.0.zip $OPENETHERUEM_ZIP
RUN echo b5a924c625de2f18981ec5514782c6eb4c14db82a8788f7084667a9d8bcb74f6 $OPENETHERUEM_ZIP | sha256sum -c \
&& unzip -j $OPENETHERUEM_ZIP openethereum -d /usr/local/bin/ \
&& chmod 755 $CLIENT_BIN \
&& rm -f $OPENETHERUEM_ZIP

# Download migration tool
ADD https://github.com/openethereum/3.1-db-upgrade-tool/archive/a497417eb22e0eb8f1f2a7b7c46a4a3eacc4db4c.zip $MIGRATION_TOOL_ZIP
RUN echo 5e9adeb3acd890a5e74f5fbc4c0ce7cb0be6b5c3942cc433afb3baa3a9dfdebb $MIGRATION_TOOL_ZIP | sha256sum -c \
&& unzip $MIGRATION_TOOL_ZIP -d /usr/local/migration_tool \
&& ( cd /usr/local/migration_tool/3.1-db-upgrade-tool-a497417eb22e0eb8f1f2a7b7c46a4a3eacc4db4c/ && cargo build )

## Configuring
### Network RPC WebSocket SecretStore IPFS
EXPOSE 30300 8545 8546 8082 5001

### Default chain and node configuration files.
COPY ./laika/laika-spec.json $CHAIN_SPEC_FILE
COPY ./laika/config.toml $NODE_HOME_DIR/chain.toml
COPY ./node-config/*.toml $NODE_HOME_DIR/

### Wrapper script for Openethereum.
COPY ./client_wrapper.sh $CLIENT_WRAPPER_SCRIPT
RUN chmod +x $CLIENT_WRAPPER_SCRIPT

### Shorthand links
RUN ln -s $NODE_HOME_DIR /config && \
    ln -s $NODE_DATA_DIR /data && \
    ln -s /usr/local/migration_tool/3.1-db-upgrade-tool-a497417eb22e0eb8f1f2a7b7c46a4a3eacc4db4c /migration_tool

COPY ./laika/VERSION /

# Start
ENTRYPOINT ["/home/openethereum/client_wrapper.sh"]
