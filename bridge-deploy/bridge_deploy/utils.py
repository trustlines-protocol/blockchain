from os import path
import json

script_directory = path.dirname(path.realpath(__file__))


def load_poa_contract(contract_name):
    with open(
        f"{script_directory}/../../submodules/poa-bridge-contracts/build/contracts/{contract_name}.json"
    ) as json_file:
        return json.load(json_file)


def load_build_contract(contract_name, file_name="contracts"):
    with open(f"{script_directory}/../build/{file_name}.json") as json_file:
        contract_data = json.load(json_file)
        return contract_data[contract_name]
