from eth_account import Account

from quickstart import utils


def test_is_wrong_password():
    def try_wrong_password():
        keystore_dict = Account.from_key("0" * 64).encrypt("password")
        try:
            Account.decrypt(keystore_dict, "wrong password")
        except Exception as err:
            return err

    assert utils.is_wrong_password_error(try_wrong_password())
