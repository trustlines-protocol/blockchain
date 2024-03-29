# This can be build with the following command:
#
#   docker build -t bridge ../. -f Dockerfile
#
# we use an intermediate image to build this image. it will make the resulting
# image a bit smaller.

FROM ubuntu:18.04@sha256:f08638ec7ddc90065187e7eabdfac3c96e5ff0f6b2f1762cf31a4f49b53000a5 as builder

WORKDIR /src

# python needs LANG
ENV LANG C.UTF-8
RUN apt-get -y update \
&& apt-get install -y --no-install-recommends python3 python3-distutils \
               python3-dev python3-venv git build-essential \
&& rm -rf /var/lib/apt/lists/*


RUN python3 -m venv /opt/bridge
ENV PATH "/opt/bridge/bin:${PATH}"
RUN pip install pip wheel setuptools
COPY ./bridge/requirements.txt .

# remove development dependencies from the end of the file
RUN sed -i -e '/development dependencies/q' requirements.txt

RUN pip install -r requirements.txt

COPY ./bridge ./bridge/
RUN pip install ./bridge/

FROM ubuntu:18.04@sha256:f08638ec7ddc90065187e7eabdfac3c96e5ff0f6b2f1762cf31a4f49b53000a5 as runner
ENV LANG C.UTF-8
RUN apt-get update \
    && apt-get install -y apt-utils python3  \
    && rm -rf /var/lib/apt/lists/*

FROM runner
COPY --from=builder /opt/bridge /opt/bridge
WORKDIR /opt/bridge
ENV PATH "/opt/bridge/bin:${PATH}"

ENTRYPOINT [ "/opt/bridge/bin/tlbc-bridge" ]
