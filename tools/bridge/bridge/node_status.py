import logging
from typing import Any, Dict, List

import attr
import gevent
import tenacity

logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True)
class NodeStatus:
    is_parity: bool
    is_light_node: bool
    is_syncing: bool
    syncing_map: Dict
    block_number: int
    latest_synced_block: int
    block_gap: List[int]
    client_version: Any = attr.ib(repr=False)


def get_node_status(w3):
    client_version = w3.clientVersion
    is_parity = client_version.startswith("Parity")
    block_number = w3.eth.blockNumber

    syncing_map = w3.eth.syncing or None

    chain_status = w3.manager.request_blocking("parity_chainStatus", [])
    node_kind = w3.manager.request_blocking("parity_nodeKind", [])

    if chain_status.blockGap is not None:
        block_gap = [int(x, 16) for x in chain_status.blockGap]
    else:
        block_gap = None

    is_light_node = node_kind.capability == "light"

    if block_gap and not is_light_node:  # warp mode syncing
        is_syncing = True
        latest_synced_block = block_gap[0]
    elif syncing_map:
        is_syncing = True
        latest_synced_block = syncing_map.currentBlock
    else:
        is_syncing = False
        latest_synced_block = block_number

    return NodeStatus(
        is_parity=is_parity,
        is_light_node=is_light_node,
        is_syncing=is_syncing,
        syncing_map=syncing_map,
        block_gap=block_gap,
        block_number=block_number,
        latest_synced_block=latest_synced_block,
        client_version=client_version,
    )


def wait_for_node_status(w3, predicate, sleep_time=5.0):
    retry = tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=5, max=120),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARN),
    )
    while True:
        node_status = retry(get_node_status)(w3)
        logger.debug("wait_for_node_status, current status: %s", node_status)
        if predicate(node_status):
            return node_status
        gevent.sleep(sleep_time)
