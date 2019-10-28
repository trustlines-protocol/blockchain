# Developer Documentation

## Branches

We use `bridge/pre-release` for release candidates and
`bridge/release` for releases.  We only merge from master to
`bridge/pre-release` and from `bridge/pre-release` to
`bridge/release`.
We never merge back to the `master` branch.

The version on the master branch should always be a `dev` version, on
`bridge/pre-release` we should only have `rc` releases and on
`bridge/release` the we only have 'prod' releases (where `prod`
doesn't appear in the version number, i.e. the version number is
always major.minor.patch)

## bumpversion

tools/bridge uses bumpversion in order to maintain it's
version. bumpversion can be used to automatically upgrade the version
in multiple files. The file `VERSION` contains the current version,
it's also maintained in `bridge/version.py` and `setup.cfg`.

bumpversion is configured via the `tools/bridge/.bumpversion.cfg`
configuration file. If you want to run bumpversion to change the
bridge's version, please cd to the `tools/bridge` directory first.


## Making a pre-release

Checkout the `bridge/pre-release` branch:

```
git checkout bridge/pre-release
git pull
git merge -m 'Merge with master branch' origin/master
cd tools/bridge
bumpversion build
```
and open a PR for that branch.

The version in the `bridge/pre-release` branch should always be a
'release candidate' version with the `rc` suffix.

## Making a release

Run the following commands:

```
git checkout bridge/release
git pull
git merge -m 'Merge with pre-release branch' origin/bridge/pre-release
bumpversion release
```

and open a PR for that branch.

After a release has been made, we should upgrade the version on the
master branch with `bumpversion patch`.
