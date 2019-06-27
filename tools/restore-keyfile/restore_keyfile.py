import json

from eth_account import Account


def restore_keyfile(priv_key, password, file_path):
    json_account = Account.encrypt(priv_key, password)
    with open(file_path, "w+") as f:
        json.dump(json_account, f)


if __name__ == "__main__":
    import sys

    restore_keyfile(sys.argv[1], sys.argv[2], sys.argv[3])
