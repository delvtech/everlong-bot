"""Bots for running everlong keepers in production.

This script connects to a remote chain and runs various calls needed
by the everlong vault for maintenance.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import NamedTuple, Sequence

from agent0 import Chain
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar, log_rollbar_exception
from eth_account.account import Account
from eth_account.signers.local import LocalAccount

from everlong_bot.everlong_types import IEverlongStrategyKeeperContract
from everlong_bot.keeper_bot import execute_keeper_call_on_vaults


def main(argv: Sequence[str] | None = None) -> None:
    """Runs the checkpoint bot.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    # pylint: disable=too-many-branches

    parsed_args = parse_arguments(argv)

    # Set up rollbar
    # TODO log additional crashes
    rollbar_environment_name = "everlong_bot"
    log_to_rollbar = initialize_rollbar(rollbar_environment_name)

    # Get env variables
    rpc_uri = os.getenv("MAINNET_RPC_URI", None)
    if rpc_uri is None:
        raise ValueError("MAINNET_RPC_URI is not set")

    keeper_contract_address = os.getenv("KEEPER_CONTRACT_ADDRESS", None)
    if keeper_contract_address is None:
        raise ValueError("KEEPER_CONTRACT_ADDRESS is not set")

    private_key = os.getenv("KEEPER_PRIVATE_KEY", None)
    if private_key is None:
        raise ValueError("KEEPER_PRIVATE_KEY is not set")

    # Set up objects
    # Get chain
    chain = Chain(rpc_uri, Chain.Config(no_postgres=True))

    # Set up keeper account
    sender: LocalAccount = Account().from_key(private_key)

    # Set up keeper contract pypechain object
    keeper_contract = IEverlongStrategyKeeperContract.factory(w3=chain._web3)(
        chain._web3.to_checksum_address(keeper_contract_address)
    )

    # Run keeper bot periodically
    while True:
        logging.info("Checking for running keeper...")

        execute_keeper_call_on_vaults(chain, sender, keeper_contract)

        time.sleep(parsed_args.check_period)


class Args(NamedTuple):
    """Command line arguments for the everlong bot."""

    check_period: int


def namespace_to_args(namespace: argparse.Namespace) -> Args:
    """Converts argprase.Namespace to Args.

    Arguments
    ---------
    namespace: argparse.Namespace
        Object for storing arg attributes.

    Returns
    -------
    Args
        Formatted arguments
    """
    return Args(
        check_period=namespace.check_period,
    )


def parse_arguments(argv: Sequence[str] | None = None) -> Args:
    """Parses input arguments.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.

    Returns
    -------
    Args
        Formatted arguments
    """
    parser = argparse.ArgumentParser(description="Runs the everlong bot")
    parser.add_argument(
        "--check-period",
        type=int,
        default=3600,  # 1 hour
        help="Number of seconds to wait between checks",
    )

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


# Run the everlong keeper bot.
if __name__ == "__main__":
    # Wrap everything in a try catch to log any non-caught critical errors and log to rollbar
    try:
        main()
    except BaseException as exc:  # pylint: disable=broad-except
        # pylint: disable=invalid-name
        _rpc_uri = os.getenv("RPC_URI", None)
        if _rpc_uri is None:
            _log_prefix = "Uncaught Critical Error in Everlong Bot:"
        else:
            _chain_name = _rpc_uri.split("//")[-1].split("/")[0]
            _log_prefix = f"Uncaught Critical Error for {_chain_name} in Everlong Bot:"
        log_rollbar_exception(exception=exc, log_level=logging.CRITICAL, rollbar_log_prefix=_log_prefix)
        raise exc
