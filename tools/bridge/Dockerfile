FROM python:3

WORKDIR /usr/src/app

COPY ./constraints.txt ./tools/bridge/requirements.txt ./tools/bridge/setup.py ./
COPY ./tools/bridge/bridge/ ./bridge/

# Remove development dependencies & Install dependencies
RUN sed -i '/requirements-dev/d' ./requirements.txt && \
pip install -c constraints.txt pip wheel setuptools && \
pip install -c constraints.txt -r requirements.txt && \
pip install -c constraints.txt -e .

CMD [ "tlbc-bridge" ]
