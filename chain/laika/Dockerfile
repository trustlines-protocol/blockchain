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
ENV OPENETHERUEM_ZIP=/usr/local/openethereum.zip

RUN mkdir -p $PARITY_HOME_DIR && \
    ls -la $PARITY_HOME_DIR


# Donload unzip
RUN  apt-get update -y && \
     apt-get upgrade -y && \
     apt-get dist-upgrade -y && \
     apt-get -y autoremove && \
     apt-get clean
RUN apt-get install -y unzip

# Download openethereum
ADD https://github.com/openethereum/openethereum/releases/download/v3.0.1/openethereum-linux-v3.0.1.zip $OPENETHERUEM_ZIP
RUN echo 8dd753058e5db77ffaede5a53418005f9c8133212448e11df9169a651cdac997 $OPENETHERUEM_ZIP | sha256sum -c \
&& unzip -j $OPENETHERUEM_ZIP openethereum -d /usr/local/bin/ \
&& mv /usr/local/bin/openethereum $PARITY_BIN \
&& chmod 755 $PARITY_BIN \
&& rm -f $OPENETHERUEM_ZIP


## Configuring
### Network RPC WebSocket SecretStore IPFS
EXPOSE 30300 8545 8546 8082 5001

### Default chain and node configuration files.
COPY ./laika/laika-spec.json $PARITY_CONFIG_FILE_CHAIN
COPY ./laika/config.toml $PARITY_HOME_DIR/chain.toml
COPY ./node-config/*.toml $PARITY_HOME_DIR/

### Wrapper script for Parity.
COPY ./parity_wrapper.sh $PARITY_WRAPPER_SCRIPT
RUN chmod +x $PARITY_WRAPPER_SCRIPT

### Shorthand links
RUN ln -s $PARITY_HOME_DIR /config && \
    ln -s $PARITY_DATA_DIR /data

COPY ./laika/VERSION /

# Start
ENTRYPOINT ["/home/parity/parity_wrapper.sh"]
