# This will build a docker image suitable for the Laika Testnet
# We basically just copy the image from an official parity docker image.
#
# You can build the image from the parent dir with this command:
#
#   docker build -f laika/Dockerfile -t tlbc-testnet-next .

FROM ubuntu:18.04@sha256:f08638ec7ddc90065187e7eabdfac3c96e5ff0f6b2f1762cf31a4f49b53000a5

## Environment
ENV HOME=/home/parity
ENV PARITY_HOME_DIR=$HOME/.local/share/io.parity.ethereum
ENV PARITY_CONFIG_FILE_CHAIN=$PARITY_HOME_DIR/trustlines-spec.json
ENV PARITY_DATA_DIR=$PARITY_HOME_DIR/chains
ENV PARITY_BIN=/usr/local/bin/parity
ENV PARITY_WRAPPER_SCRIPT=$HOME/parity_wrapper.sh

RUN mkdir -p $PARITY_HOME_DIR && \
    ls -la $PARITY_HOME_DIR


# Download parity executable, check that it's what we expect
ADD https://releases.parity.io/ethereum/v2.3.6/x86_64-unknown-linux-gnu/parity $PARITY_BIN
RUN echo a99f7ba6bc90dd128acea7cc2c730279c6da6783ffcae521d6fe4ff8c3eee0d9 $PARITY_BIN | sha256sum -c
RUN chmod 755 $PARITY_BIN


## Configuring
### Network RPC WebSocket SecretStore IPFS
EXPOSE 30300 8545 8546 8082 5001

### Default chain and node configuration files.
COPY ./laika/laika-spec.json $PARITY_CONFIG_FILE_CHAIN
COPY ./*-config.toml $PARITY_HOME_DIR/

### Wrapper script for Parity.
COPY ./parity_wrapper.sh $PARITY_WRAPPER_SCRIPT
RUN chmod +x $PARITY_WRAPPER_SCRIPT

### Shorthand links
RUN ln -s $PARITY_HOME_DIR /config && \
    ln -s $PARITY_DATA_DIR /data

COPY ./laika/VERSION /

# Start
ENTRYPOINT ["/home/parity/parity_wrapper.sh"]
