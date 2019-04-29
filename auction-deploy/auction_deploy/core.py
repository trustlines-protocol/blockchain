import json
import pkg_resources


def load_contracts_json():
    resource_package = __name__
    stream = pkg_resources.resource_stream(resource_package, "contracts.json")
    json_string = stream.read().decode()
    stream.close()
    return json.loads(json_string)
