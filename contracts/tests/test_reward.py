import pytest

from eth_utils import to_wei

from eth_tester.exceptions import TransactionFailed


def test_validator_is_rewarded_1_eth(
    reward_contract, system_address, emission_address, validators
):
    assert reward_contract.functions.reward([validators[0]], [0]).call(
        {"from": system_address}
    ) == [[validators[0], emission_address], [to_wei(1, "ether"), 0]]


def test_bridge_is_rewarded_requested_amount(
    reward_contract, system_address, bridge_address, emission_address, validators
):
    for amount in [50, 100]:
        reward_contract.functions.addExtraReceiver(amount, bridge_address).transact(
            {"from": bridge_address}
        )
    assert reward_contract.functions.reward([validators[0]], [0]).call(
        {"from": system_address}
    ) == [
        [validators[0], emission_address, bridge_address],
        [to_wei(1, "ether"), 0, 150],
    ]


def test_bridge_reward_is_reset_on_reward(
    reward_contract, system_address, emission_address, bridge_address, validators
):
    reward_contract.functions.addExtraReceiver(100, bridge_address).transact(
        {"from": bridge_address}
    )
    reward_contract.functions.reward([validators[0]], [0]).transact(
        {"from": system_address}
    )
    assert reward_contract.functions.reward([validators[0]], [0]).call(
        {"from": system_address}
    ) == [[validators[0], emission_address], [to_wei(1, "ether"), 0]]


def test_only_system_can_reward(reward_contract, malicious_validator_address):
    with pytest.raises(TransactionFailed):
        reward_contract.functions.reward([malicious_validator_address], [0]).call(
            {"from": malicious_validator_address}
        )


def test_only_bridge_can_request(reward_contract, malicious_validator_address):
    with pytest.raises(TransactionFailed):
        reward_contract.functions.addExtraReceiver(
            100, malicious_validator_address
        ).transact({"from": malicious_validator_address})


def test_exactly_one_validator_is_rewarded(
    reward_contract, system_address, validators, malicious_validator_address
):
    with pytest.raises(TransactionFailed):
        reward_contract.functions.reward([], []).call({"from": system_address})

    with pytest.raises(TransactionFailed):
        reward_contract.functions.reward(
            [validators[0], malicious_validator_address], [0, 0]
        ).call({"from": system_address})


def test_kind_must_be_zero(
    reward_contract, system_address, malicious_validator_address
):
    with pytest.raises(TransactionFailed):
        assert reward_contract.functions.reward(
            [malicious_validator_address], [1]
        ).call({"from": system_address})
