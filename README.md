# Trustlines Blockchain

- [Run Local Peer](#run-local-peer)
  - [Quickstart](#quickstart)
  - [System Time](#system-time)
  - [With Docker](#with-docker)
    - [Pre-Requisites](#pre-requisites)
    - [Usage](#Usage)
    - [Examples](#Examples)
    - [Observer](#Observer)
    - [Participant](#Participant)
    - [Validator](#Validator)
    - [Create New Account](#create-new-account)
  - [Without Docker](#without-docker)
    - [Pre-Requisites](#pre-requisites)
    - [Creating An Account](#creating-an-account)
    - [Setup For Users Using Only CLI](#setup-for-users-using-only-cli)
    - [Setup For Validators Using Only CLI](#setup-for-validators-using-only-cli)
- [Backups](#backups)
- [Development](#development)
  - [Build Own Image](#build-own-image)
  - [Upload Image](#upload-image)
  - [Running Tests on Contracts](#running-tests-on-contracts)

## Run Local Peer

Please make sure you have access to a continuously running machine, if you like to participate as validator to the network.

### Quickstart

To make starting a validator node for the Trustlines Network as quick as possible, the _quickstart_ script can be used. Simply download and run
the script. The script will make sure to have everything that is necessary, create a new account for you and start the _Parity_ client with all
requested arguments. This includes the establishment of an automatic update service.
The script can be called multiple times without problems, so it checks what is already there and will at least update all service processes.
_Parity_ will restart automatically on fails.

```sh
$ wget -O quickstart.sh https://github.com/trustlines-protocol/blockchain/raw/master/quickstart.sh && bash quickstart.sh
```

Follow the instructions to insert your password. If you want to restart the node or want to make sure it runs on the most recent version, just
rerun the script.

---

### System Time

Due to the way the block validation works and is synchronized, it is essential to make sure your host system has the correct time configuration. On recent Ubuntu systems, for example, this should already be the case. You can check the settings on such systems using ```timedatectl```.

On other operating systems you should check if your time is synchronized with an [NTP server](https://www.pool.ntp.org/).

---

### With Docker

The following instructions explain how to start a local peer with the _Docker_ image. In fact it use a pre-configured [Parity
Ethereum](https://www.parity.io/) client, combined with a set-up wrapper, to make connecting as easy as possible. The image is prepared to be
used in three different scenarios: as observer, to participate and connect as validator.

#### Pre-Requisites

To make it work, a complete [Docker](https://www.docker.com/) environment is necessary to be installed on your system. Please take a look into
the [official documentation](https://docs.docker.com/install/#general-availability) and use the instructions for your respective OS. Some
niche operating systems are not mentioned there but still provide packages (e.g. [ArchLinux - docker](https://www.archlinux.org/packages/community/x86_64/docker/)).
Make sure that your user is added to the `docker` user-group on _Unix_ systems, if you can not access root permissions to run containers.

#### Usage

To run the parity client for the Trustlines Network you first have to pull the image from
[DockerHub](https://hub.docker.com/r/trustlines/tlbc-testnet). It does not matter in which directory your are working this step, cause it will
be added to _Dockers_ very own database. Afterwards calling the help should give a first basic overview how to use.

```
$ docker pull trustlines/tlbc-testnet
$ docker run trustlines/tlbc-testnet --help

 NAME
   Parity Wrapper

 SYNOPSIS
   parity_wrapper.sh [-r] [role] [-a] [address] [-p] [arguments]

 DESCRIPTION
   A wrapper for the actual Parity client to make the Docker image easy usable by preparing the Parity client for
   a set of predefined list of roles the client can take without have to write lines of arguments on run Docker.

 OPTIONS
   -r [--role]         Role the Parity client should use.
                       Depending on the chosen role Parity gets prepared for that role.
                       Selecting a specific role can require further arguments.
                       Checkout ROLES for further information.

   -a [--address]      The Ethereum address that parity should use.
                       Depending on the chosen role, the address gets inserted at the right
                       place of the configuration, so Parity is aware of it.
                       Gets ignored if not necessary for the chosen role.

   -p [--parity-args]  Additional arguments that should be forwarded to the Parity client.
                       Make sure this is the last argument, cause everything after is
                       forwarded to Parity.

 ROLES
   The list of available roles is:

   observer
     - Is the default role
     - Does only watch for propagated blocks.
     - Non arguments required at all.

   participant
     - Connects to an account to being able to create transactions.
     - Requires the address argument.
     - Needs the password file and the key-set. (see FILES)

   validator
     - Connect as authority to the network for validating blocks.
     - Requires the address argument.
     - Needs the password file and the key-set. (see FILES)

 FILES
   The configuration folder for Parity takes place at /home/parity/.local/share/io.parity.ethereum.
   Alternately the shorthand symbolic link at /config can be used.
   Parity's data base is at /home/parity/.local/share/io.parity.ethereum/chains or available trough /data as well.
   To provide custom files in addition bind a volume through Docker to the sub-folder called 'custom'.
   The password file is expected to be placed in the custom configuration folder names 'pass.pwd'.
   The key-set is expected to to be placed in the custom configuration folder under 'keys/Trustlines/'
   Besides from using the pre-defined locations, it is possible to define them manually thought the parity
   arguments. Checkout their documentation to do so.
```

#### Examples

Besides the original help, the following sections provide some example instructions how to get started for the different selectable roles.

##### Observer

For observing the Trustlines blockchain absolutely nothing has to be prepared for the client image. A simple pull and run is all that is needed.
Since the loss of the block data when the container restarts would lead to a long startup procedure where the clients needs to sync up first, it is
recommended to use a local volume bound in to save the data outside of the _Docker_ container. Furthermore the node should be able to explore the network and establish
connections to other peers. Therefore the port `30300` has to be public available and mapped to the containers one.

```sh
$ mkdir ./database
$ docker run -ti -v $(pwd)/database:/data -p 30300:30300 trustlines/tlbc-testnet
```

##### Participant

If the client should be connected with an account to sign transactions and interact with the blockchain, the help output states that the accounts
key-pair, address and the related password is necessary to provide. To make all files accessible to the _Docker_ container needs a binded volume.
Therefore create a new folder to do so. (The following instructions expect the folder `config` inside the current working directory. Adjust them if
you prefer a different location.) Inside a directory for the keys with another sub-directory for the Trustlines chain is used by _Parity_. Your
key-file has to be placed there. Afterwards the keys password has to be stored into a file directly inside the `config` folder. (To make use of the
default configurations without adjustment, the file has to be called `pass.pwd`).
If you have no account already or want to create a new one for this purpose checkout [this section](#create-new-account). Using so the previous
paragraph as well as the first 2-3 instructions can be ignored. Anyways the password used there has to be stored as shown below.
Finally the client has to be started with the volume bound, the correct role and the address to use. Be aware that _Docker_ requires absolute paths.

```sh
$ mkdir -p ./config/keys/Trustlines
$ cp /path/to/my/key ./config/keys/Trustlines/
$ echo "mysupersecretpassphrase" > ./config/pass.pwd
$ mkdir ./database
$ docker run -ti -v $(pwd)/database:/data -v $(pwd)/config:/config/custom -p 30300:30300 trustlines/tlbc-testnet --role participant --address MY_ADDRESS
```

##### Validator

If you are an authority of the Trustlines Network and want to use the client as validator, follow the instructions to run as
[participant](#participant) except starting the _Docker_ container. For information how to become a validator have a look
[here](#become-an-authority).
As soon as you have set up the `config` folder with your account that is registered as authority, simply start the client with the role `validator`
and the wrapper will make sure to set up everything required to do so.

```sh
...
$ docker run -ti -v $(pwd)/database:/data -v $(pwd)/config:/config/custom -p 30300:30300 trustlines/tlbc-testnet --role validator --address MY_ADDRESS
```

#### Create New Account

If no already existing account is available or a new one should be created anyway, _Parity_ could be used to do so. Please consider other
options like [MetaMask](https://metamask.io/), [Mist](https://github.com/ethereum/mist) or any other (online) wallet tool.
In relation to the instructions for the [participant](#participant) and [validator](#validator) roles, we use the folder called `config` to
bind as _Docker_ volume to _Parity_. Afterwards the key will be placed there and the first steps of these instructions can be skipped.

```sh
$ mkdir ./config
$ docker run -ti -v $(pwd)/config/:/config/custom trustlines/tlbc-testnet --parity-args account new
```

_Parity_ will ask for a password, that should be stored by you to `./config/pass.pwd` afterwards. The address corresponding to the generated
private key gets printed out on the commandline at the last line starting with `0x`. Please copy it for the later use. It will be needed for
the `--address` argument where it will be added in plain text.

---

### Without Docker

This section explains how to start a local peer without using the _Docker_ image.

#### Pre-Requisites

- parity version 2.0.9
- the file: "trustlines-spec.json"

#### Creating An Account

To interact with the trustlines chain, one needs a private key corresponding to an address usable on the chain. If you already possess such a key, you can skip this section.

To start with, create a folder to store everything related to the Trustlines chain, move the trustlines-spec.json file to this folder and change to this folder:

```sh
mkdir trustlines-chain
mv trustlines-spec.json trustlines-chain/trustlines-spec.json
cd trustlines-chain
```

You can then create an account with the command:

```sh
parity account new --chain trustlines-spec.json -d [path/to/node/foler]
```

For the rest of this documentation to become a validator we will assume you ran:

```sh
parity account new --chain trustlines-spec.json -d validator_node
```

You will be prompted to enter a password twice to protect this private key. You need to remember this password and use it whenever you want to use the private key. After successfully creating an account, you will see displayed the public address corresponding to that account (in format 0x6c4cbad9865dbfda5d5c5e2e353623b07ace71e6), keep that address somewhere.

For running a node as a validator, you will need to store your password in a file.

```sh
echo [mypassword] > password.pwd
```

#### Setup For Users Using Only CLI

These are the steps to run a node as a simple user.

Independently of whether you created an account or not, you can start a node to sync with the trustlines chain with the following command:

```sh
parity --chain trustlines-spec.json -d user_node --auto-update=none --no-download
```

#### Setup For Validators Using Only CLI

These are the steps to run a node as a validator, make sure you are a validator before following these steps.

If you just created an account following the "Creating an account" section and stored your password in the file "password.pwd", you can start a node with the following command, replacing [address] with your address given during account creation:

```sh
parity --chain trustlines-spec.json -d validator_node --auto-update=none --no-download --password=password.pwd --max-peers=100 --author=[address] --engine-signer=[address] --force-sealing --reseal-on-txs=none --min-gas-price="1" --tx-queue-per-sender=100
```

Otherwise, you need to adjust some parameters. You need to provide the path to your private key in "--keys-path=[path]", the path to your password protecting this key in "--password=[path]" as well as your address in "--author=[address]" and "--engine-signer=[address]"

```sh
parity --chain trustlines-spec.json -d validator_node --auto-update=none --no-download --keys-path=[path/to/keys] --password=[path/to/password] --max-peers=100 --author=[address] --engine-signer=[address] --force-sealing --reseal-on-txs=none --min-gas-price="1" --tx-queue-per-sender=100
```

---

## Backups

Please make sure to backup your private key and associated password! Depending on your setup, the key can be found in general in _Parity's_
home directory (per default `~/.local/share/io.parity.ethereum`) under `keys/Trustlines/`. In case of using the docker image, it can be found
in the volume bound to `/config` relative to [these instructions](#participant). When working with the quickstart script, the key is placed in
`./trustlines/config/keys/Trustlines` relative to where you have run the script.


---

## Development

### Build Own Image

To build the _Docker_ image, checkout this repository and run `docker build` with your preferred tag name. As the context of
the build must be the project root, the path to the `Dockerfile` has to be specified manually.

```sh
$ git clone https://github.com/trustlines-protocol/blockchain
$ docker build -f docker/Dockerfile -t MY_TAGNAME .
$ docker run ... MY_TAGNAME ...
```

### Upload Image

The built image is public available at [DockerHub](https://hub.docker.com/). To upload a new version make sure to have access to the
_trustlines_ organization. If permissions are given, the local build has to be tagged and then pushed.
Please replace `USERNAME` with your own account name on _DockerHub_ and `LOCAL_IMAGE` with the tag name you have given the image while building.
The example below uses the `:latest` tag postfix which is the default one used by _DockerHub_ when pulling an image. If you want to provide an
additional tag (e.g. for sub-versions), adjust the name when tagging.

```sh
$ echo "yoursecretpassword" | docker login --username USERNAME --password-stdin
$ docker tag LOCAL_IMAGE trustlines/tlbc-testnet:latest
$ docker push trustlines/tlbc-testnet:latest
```

### Running Tests on Contracts

First, download and install the solidity compiler solc into bin for compiling the
contracts. You can follow the [official installation documentation](https://solidity.readthedocs.io/en/v0.4.24/installing-solidity.html) or type the following recommand command:

``curl -L -o $HOME/bin/solc https://github.com/ethereum/solidity/releases/download/v0.5.8/solc-static-linux && chmod +x $HOME/bin/solc``

To start developing, you should change directory to the contracts directory ``cd contracts``.
Then, install the development dependencies into a venv
with ``pip install -c constraints.txt -r requirements.txt``

You can run then run the tests with ``pytest tests/``.
To check for linter errors in the contract code you can run ``solium --dir contracts/``.
To check for linter errors in the python code you can run ``flake8 tests/``.
