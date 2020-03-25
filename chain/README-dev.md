# Developer Documentation

## Branches

We use `laika-node/pre-release`/`tlbc-node/pre-release` for release candidates
and `laika-node/release`/`tlbc-node/release` for releases. We only merge from
`master` to `*/pre-release`, from `*/pre-release` to `*/release` and from
`*/release` back to `master`.

The version on the master branch should always be a `dev` version. The
`*/pre-release` branches should always have a `rc` version and on `*/release`
branches we only have `prod` releases (where `prod` doesn't appear in the
version number, i.e. the version number is always `major.minor.patch`).

## bumpversion

Both chains use [bumpversion](https://pypi.org/project/bumpversion/) in order to
maintain their version. bumpversion can be used to automatically upgrade the
current version in the respective `VERSION` file within the `chain/laika` and
`chain/tlbc` directories.

bumpversion is configured via the `.bumpversion.cfg` configuration files in
`chain/laika` and `chain/tlbc`. If you want to run bumpversion to change
a chain's version, please change to the chain's directory first. Note that
bumping the version will automatically create a new commit.

## Making A Pre-release

Adopt the following instructions for the respective chain (demonstrated for
the Laika test network) new version:

```sh
$ git checkout master
$ git pull
$ git checkout -b laika-node/prepare/pre-release-<version>
$ cd chain/laika
$ bumpversion release
```

and open a PR for this new branch to `laika-node/pre-release`.

The version in the `*/pre-release` branches should always be a 'release candidate'
version with the `rc` suffix.

## Making A Release

Run the following commands and adopt for the respective chain (demonstrated for
the Laika test network) and new version:

```sh
$ git checkout laika-node/pre-release
$ git pull
$ git checkout -b laika-node/prepare/release-<version>
$ cd chain/laika
$ bumpversion release
```

and open a PR for this new branch to `laika-node/release`.

The version in the `*/release` branches should always be a 'release' version
with a clean version number.

## Merge Release Back

After a release has been made, it should been merged back to the `master`
branch. Adopt the following instructions for the respective chain (demonstrated
for the Laika test network) and the next version:

```sh
$ git checkout laika-node/release
$ git pull
$ git checkout -b laika-node/prepare/master-<next-version>
$ cd chain/laika
$ bumpversion path
```

and open a PR for this branch to `master`.

The version in the `master` branch should always be a 'development' version with
the `dev` suffix.

## Release Checklist

**Attention:**
Never use the `rebase and merge` functionality to finalize a PR at GitHub during
the release process. This will create new commits and causes a different history
for the release relevant branches.

0. Prerequisite: The `master` branch contains the version to be released.
1. Follow the instructions to [make a pre-release](#making-a-pre-release).
   Merging this PR will build the Docker image and pushes it to Docker Hub under
   either `trustlines/tlbc-testnet-next:pre-release` (for testnet pre-releases)
   or `trustlines/tlbc-node-next:pre-release` (for mainnet pre-releases).
2. Test the `pre-release` version:
   - Pull the newly built image from Docker Hub.
   - Double check that changes to the chain spec (if any) are correct.
   - Run the node and check that it finds other peers, connects to them, and
     starts syncing the chain.
   - Run the node in a pre-existing environment set up using the quickstart
     script and check that it connects to peers and continues to stay at the
     head of the chain.
   - Perform any additional tests compelled by the specifics of the update.
3. Follow the instructions to [make a release](#making-a-release).
   Wait for a PR review confirming that the necessary testing steps have been
   performed and merge it. This will trigger the build of the release Docker
   image.
4. Authorize the release of the image to Docker Hub in CircleCI.
5. Check that CircleCI was successful and a that there is a new image under
   `trustlines/tlbc-testnet:release` or `trustlines/tlbc-node:release`,
   respectively.
6. Follow the instructions to [merge the release back](#merge-release-back) to
   `master`.
