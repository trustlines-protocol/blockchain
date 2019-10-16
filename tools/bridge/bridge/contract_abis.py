MINIMAL_ERC20_TOKEN_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    }
]


HOME_BRIDGE_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "validatorsRequiredPercent",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "", "type": "bytes32"}],
        "name": "transferState",
        "outputs": [
            {"name": "numConfirmations", "type": "uint16"},
            {"name": "isCompleted", "type": "bool"},
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "transferHash", "type": "bytes32"},
            {"name": "transactionHash", "type": "bytes32"},
            {"name": "amount", "type": "uint256"},
            {"name": "recipient", "type": "address"},
        ],
        "name": "confirmTransfer",
        "outputs": [],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "_proxy", "type": "address"},
            {"name": "_validatorsRequiredPercent", "type": "uint256"},
        ],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "transferHash", "type": "bytes32"},
            {"indexed": False, "name": "transactionHash", "type": "bytes32"},
            {"indexed": False, "name": "amount", "type": "uint256"},
            {"indexed": False, "name": "recipient", "type": "address"},
            {"indexed": True, "name": "validator", "type": "address"},
        ],
        "name": "Confirmation",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "transferHash", "type": "bytes32"},
            {"indexed": False, "name": "transactionHash", "type": "bytes32"},
            {"indexed": False, "name": "amount", "type": "uint256"},
            {"indexed": False, "name": "recipient", "type": "address"},
            {"indexed": False, "name": "coinTransferSuccessful", "type": "bool"},
        ],
        "name": "TransferCompleted",
        "type": "event",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "validatorProxy",
        "outputs": [{"name": "", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
]

MINIMAL_VALIDATOR_PROXY_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "", "type": "address"}],
        "name": "isValidator",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    }
]
