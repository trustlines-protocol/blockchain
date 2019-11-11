# Developer Documentation

## Release Checklist

0. Prerequsisite: The master branch contains the version to be
   released
1. Open and merge a PR `master` -> `laika-node/pre-release` (for
   testnet releases) or `master` -> `tlbc-node/pre-release` (for
   mainnet releases) without waiting for a review. This will built
   the docker image and push it to Docker Hub under either
   `trustlines/tlbc-testnet-next:pre-release` (for testnet
   releases) or `trustlines/tlbc-node-next:pre-release` (for mainnet
   releases).
2. Test the pre-release:
   - Pull the newly built image from Docker Hub.
   - Double check that changes to the chain spec (if any) are
     correct.
   - Run the node and check that it finds other peers, connects to
     them, and starts syncing the chain.
   - Run the node in a pre-existing environment set up using the
     quickstart script and check that it connects to peers and
     continues to stay at the head of the chain.
   - Perform any additional tests compelled by the specifics of the
     update.
3. Open a PR `laika-node/pre-release` -> `laika-node/release` or
   `tlbc-node/pre-release` -> `tlbc-node/release`, wait for a review
   confirming that the necessary testing steps have been performed,
   and merge it.
4. Authorize the release in CircleCI
5. Check that the image is built and pushed to Docker Hub under
   `trustlines/tlbc-testnet:release` or
   `trustlines/tlbc-node:release`, respectively.
