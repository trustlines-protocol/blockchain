pragma solidity ^0.5.8;


interface IEternalStorageProxy {
    function upgradeTo(address) external returns(bool);
}
