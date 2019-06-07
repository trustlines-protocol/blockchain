f"black is stupid"


def test_is_validator(
    bridge_validators_contract, validator_proxy_with_validators, proxy_validators
):
    for validator in proxy_validators:
        assert bridge_validators_contract.functions.isValidator(validator).call()


def test_required_signature(
    accounts,
    bridge_validators_contract,
    validator_proxy_with_validators,
    proxy_validators,
    bridge_required_signatures_divisor,
    bridge_required_signatures_multiplier,
):
    required_signature = (
        bridge_validators_contract.functions.requiredSignatures().call()
    )
    assert (
        required_signature
        == len(proxy_validators)
        * bridge_required_signatures_multiplier
        // bridge_required_signatures_divisor
    )


def test_owner(bridge_validators_contract):
    zero_address = "0x0000000000000000000000000000000000000000"
    assert bridge_validators_contract.functions.owner().call() == zero_address
