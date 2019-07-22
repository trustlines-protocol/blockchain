FROM python:3

WORKDIR /usr/src/app

COPY ./constraints.txt ./tools/bridge/requirements.txt ./tools/bridge/setup.py ./
COPY ./tools/bridge/bridge/ ./bridge/

# Remove development dependencies & Install dependencies
RUN sed -i '/requirements-dev/d' ./requirements.txt && \
pip install -c constraints.txt pip wheel setuptools && \
pip install -c constraints.txt -r requirements.txt && \
pip install -c constraints.txt -e .

# TODO: Replace with ENV Config or mounted file
RUN echo 'home_rpc_url = "http://node_home:8545"' > config.toml
RUN echo 'foreign_rpc_url = "http://node_foreign:8545"' >> config.toml
RUN echo 'token_contract_address = "0x20fE562d797A42Dcb3399062AE9546cd06f63280"' >> config.toml
RUN echo 'foreign_bridge_contract_address = "0x83a30dD54a744c60190548af8d983719116eff4a"' >> config.toml

CMD [ "tlbc-bridge", "--config", "./config.toml" ]
