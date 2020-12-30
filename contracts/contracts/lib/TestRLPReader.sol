pragma solidity ^0.6.5;

/**
 * The sole purpose of this file is to be able to test the internal functions
 * of the RLPReader library contract.
 */

import "./RLPReader.sol";

contract TestRLPReader {
    fallback() external {}

    function testToRlpItem(bytes memory _rlpEncodedItem)
        public
        pure
        returns (uint length, uint memPtr)
    {
        RLPReader.RLPItem memory rlpItem = RLPReader.toRlpItem(_rlpEncodedItem);
        return (rlpItem.len, rlpItem.memPtr);
    }

    function testIsList(bytes memory _rlpEncodedItem)
        public
        pure
        returns (bool)
    {
        RLPReader.RLPItem memory rlpItem = RLPReader.toRlpItem(_rlpEncodedItem);
        return RLPReader.isList(rlpItem);
    }

    function testToBoolean(bytes memory _rlpEncodedItem)
        public
        pure
        returns (bool)
    {
        RLPReader.RLPItem memory rlpItem = RLPReader.toRlpItem(_rlpEncodedItem);
        return RLPReader.toBoolean(rlpItem);
    }

    function testToBytes(bytes memory _rlpEncodedItem)
        public
        pure
        returns (bytes memory)
    {
        RLPReader.RLPItem memory rlpItem = RLPReader.toRlpItem(_rlpEncodedItem);
        return RLPReader.toBytes(rlpItem);
    }

    function testToAddress(bytes memory _rlpEncodedItem)
        public
        pure
        returns (address)
    {
        RLPReader.RLPItem memory rlpItem = RLPReader.toRlpItem(_rlpEncodedItem);
        return RLPReader.toAddress(rlpItem);
    }

    function testToUint(bytes memory _rlpEncodedItem)
        public
        pure
        returns (uint)
    {
        RLPReader.RLPItem memory rlpItem = RLPReader.toRlpItem(_rlpEncodedItem);
        return RLPReader.toUint(rlpItem);
    }

    function testGetItemUint(uint index, bytes memory _rlpEncodedItem)
        public
        pure
        returns (uint)
    {
        RLPReader.RLPItem memory rlpItem = RLPReader.toRlpItem(_rlpEncodedItem);
        return RLPReader.toUint(RLPReader.toList(rlpItem)[index]);
    }
}
