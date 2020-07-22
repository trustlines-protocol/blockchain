# Openethereum Configuration

This directory contains the configuration files for the Openethereum client
To get a valid configuration you need to combine

- `base.toml`

with one of the files for a selected role

- `observer-role.toml`
- `participant-role.toml`
- `validator-role.toml`

and one of the chain specific files

- `../laika/config.toml`
- `../tlbc/config.toml`

Because the files will just be concatenated, this only works with disjoint
Openethereum configurations.
