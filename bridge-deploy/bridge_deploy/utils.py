import json


def load_poa_contract(contract_name):
    with open(
        f"../poa-bridge-contracts/build/contracts/{contract_name}.json"
    ) as json_file:
        return json.load(json_file)


def load_build_contract(contract_name, path="./build/", file_name="contracts"):
    with open(f"{path}{file_name}.json") as json_file:
        contract_data = json.load(json_file)
        return contract_data[contract_name]
