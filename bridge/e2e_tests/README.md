# Bridge End-to-End Tests

Setup with two local _Parity_ nodes which represent the foreign and home chain.
The deploy tools are applied to setup the token bridge with all dependencies and
links between the components. Finally the bridge clients are connected to the
networks and a transfer through the bridge is tested.

## Parameter

- `-b` cause to rebuild all _Docker_ images which are retrieved from a registry
- `-p` re-pull _Docker_ images from registry (_DockerHub_)
- `-s` silent the output of commands the script executes (which are meant for CI)
