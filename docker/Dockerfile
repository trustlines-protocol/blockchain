# Build Image
FROM ubuntu:18.04 as builder

## Preparations
WORKDIR /build

### Install package depenencies
RUN apt-get -y update && \
    apt-get install -y --force-yes --no-install-recommends \
      curl git ca-certificates make g++ libudev-dev cmake \
      && \
    apt-get clean

### Set-up RustUp
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH=/root/.cargo/bin:$PATH


## Parity
### Environment
ARG PARITY_BUILD_DIR=/build/parity
ARG PARITY_SOURCE_URL="https://github.com/paritytech/parity-ethereum "
ARG PARITY_BRANCH="stable"

### Building
RUN git clone --depth 1 --branch $PARITY_BRANCH $PARITY_SOURCE_URL $PARITY_BUILD_DIR && \
    cd $PARITY_BUILD_DIR && \
    cargo build --release --features final

# ---


# Client Image
FROM ubuntu:18.04 as client

## Environment
ENV HOME=/home/parity
ENV PARITY_HOME_DIR=$HOME/.local/share/io.parity.ethereum
ENV PARITY_CONFIG_FILE_CHAIN=$PARITY_HOME_DIR/trustlines-spec.json
ENV PARITY_CONFIG_FILE_TEMPLATE=$PARITY_HOME_DIR/config-template.toml
ENV PARITY_DATA_DIR=$PARITY_HOME_DIR/chains
ENV PARITY_BIN=/usr/local/bin/parity
ENV PARITY_WRAPPER_SCRIPT=$HOME/parity_wrapper.sh

RUN mkdir -p $PARITY_HOME_DIR && \
    ls -la $PARITY_HOME_DIR


## Get the build binaries from the previous image.
## (using environment variable from previous image not possible...)
COPY --from=builder /build/parity/target/release/parity $PARITY_BIN

## Configuring
### Network RPC WebSocket SecretStore IPFS
EXPOSE 30300 8545 8546 8082 5001

### Default chain and node configuration files.
COPY config/trustlines-spec.json $PARITY_CONFIG_FILE_CHAIN
COPY config/user-config.toml $PARITY_CONFIG_FILE_TEMPLATE

### Wrapper script for Parity.
COPY docker/parity_wrapper.sh $PARITY_WRAPPER_SCRIPT
RUN chmod +x $PARITY_WRAPPER_SCRIPT

### Shorthand links
RUN ln -s $PARITY_HOME_DIR /config && \
    ln -s $PARITY_DATA_DIR /data


# Start
ENTRYPOINT ["/home/parity/parity_wrapper.sh"]
