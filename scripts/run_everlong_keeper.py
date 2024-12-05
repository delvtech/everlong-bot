"""Bots for running everlong keepers in production."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import NamedTuple, Sequence

from agent0 import Chain
from agent0.hyperlogs.rollbar_utilities import (initialize_rollbar,
                                                log_rollbar_exception)
from eth_account.account import Account
from eth_account.signers.local import LocalAccount

from everlong_bot.everlong_types.IEverlongStrategyKeeper import \
    IEverlongStrategyKeeperContract
from everlong_bot.keeper_bot import execute_keeper_calls


def main(argv: Sequence[str] | None = None) -> None:
    """Runs the checkpoint bot.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    # pylint: disable=too-many-branches

    parsed_args = parse_arguments(argv)

    rollbar_environment_name = "everlong_bot"
    log_to_rollbar = initialize_rollbar(rollbar_environment_name)

    # Initialize
    keeper_contract_address = None
    # TODO Abstract this method out for infra scripts
    # Get the rpc uri from env variable
    rpc_uri = os.getenv("RPC_URI", None)
    if rpc_uri is None:
        raise ValueError("RPC_URI is not set")

    chain = Chain(rpc_uri, Chain.Config(no_postgres=True))

    # Get the registry address from environment variable
    keeper_contract_address = os.getenv("KEEPER_CONTRACT_ADDRESS", None)
    if keeper_contract_address is None:
        raise ValueError("KEEPER_CONTRACT_ADDRESS is not set")

    # Look for `CHECKPOINT_BOT_KEY` env variable
    # If it exists, use the existing key and assume it's funded
    # If it doesn't exist, create a new key and fund it (assuming this is a local anvil chain)
    private_key = os.getenv("KEEPER_BOT_KEY", None)
    if private_key is None:
        raise ValueError("KEEPER_BOT_KEY is not set")

    sender: LocalAccount = Account().from_key(private_key)

    keeper_contract = IEverlongStrategyKeeperContract.factory(w3=chain._web3)(chain._web3.to_checksum_address(keeper_contract_address))

    while True:
        logging.info("Checking for running keeper...")

        execute_keeper_calls(sender, keeper_contract)

        time.sleep(3600)



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


# Run the checkpoint bot.
if __name__ == "__main__":
    # Wrap everything in a try catch to log any non-caught critical errors and log to rollbar
    try:
        main()
    except BaseException as exc:  # pylint: disable=broad-except
        # pylint: disable=invalid-name
        _rpc_uri = os.getenv("RPC_URI", None)
        if _rpc_uri is None:
            _log_prefix = "Uncaught Critical Error in Checkpoint Bot:"
        else:
            _chain_name = _rpc_uri.split("//")[-1].split("/")[0]
            _log_prefix = f"Uncaught Critical Error for {_chain_name} in Checkpoint Bot:"
        log_rollbar_exception(exception=exc, log_level=logging.CRITICAL, rollbar_log_prefix=_log_prefix)
        raise exc
