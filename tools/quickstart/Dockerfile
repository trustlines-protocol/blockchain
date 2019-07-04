# This can be build with the following command:
#
#   docker build -t quickstart ../.. -f Dockerfile
#
# we use an intermediate image to build this image. it will make the resulting
# image a bit smaller.

FROM ubuntu:18.04@sha256:f08638ec7ddc90065187e7eabdfac3c96e5ff0f6b2f1762cf31a4f49b53000a5 as base
FROM base as builder
# python needs LANG
ENV LANG C.UTF-8
ENV PIP_DISABLE_PIP_VERSION_CHECK 1

RUN apt-get update \
    && apt-get install -y apt-utils python3 python3-distutils python3-dev python3-venv build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/quickstart/
ENV PATH="/opt/quickstart/bin:${PATH}"

WORKDIR /src

# enable docker to cache some install steps
COPY tools/quickstart/constraints.txt /src/
RUN pip install -c constraints.txt pip wheel setuptools
COPY tools/quickstart/requirements.txt /src/
# remove development dependencies from the end of the file
RUN sed -i -e '/development dependencies/q' requirements.txt
RUN pip install -c constraints.txt -r requirements.txt

COPY tools/quickstart /src/
# we need to copy the symlinked file again, otherwise we have a symlink that points to nowhere
COPY tools/quickstart/constraints.txt /src/
RUN pip install -c constraints.txt .

FROM base as runner
ENV LANG C.UTF-8
RUN apt-get update \
    && apt-get install -y apt-utils python3 \
    && rm -rf /var/lib/apt/lists/*

FROM runner
COPY --from=builder /opt/quickstart /opt/quickstart
ENV PATH="/opt/quickstart/bin:${PATH}"
