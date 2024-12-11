"""Bots for running everlong keepers in production."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import NamedTuple, Sequence

from agent0 import LocalChain, LocalHyperdrive
from agent0.hyperfuzz.system_fuzz import run_fuzz_bots
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar, log_rollbar_exception
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from fixedpointmath import FixedPoint
from pypechain.core import PypechainCallException
from web3 import Web3
from web3.exceptions import ContractCustomError

from everlong_bot.everlong_types import IEverlongStrategyKeeperContract
from everlong_bot.keeper_bot import execute_keeper_call_on_vaults

MAINNET_WHALE_ADDRESSES = {
    # DAI
    "0x6B175474E89094C44Da98b954EedeAC495271d0F": "0xf6e72Db5454dd049d0788e411b06CfAF16853042",
}


def _fuzz_ignore_errors(exc: Exception) -> bool:
    """Function defining errors to ignore for pausing chain during fuzzing."""
    # pylint: disable=too-many-return-statements
    # pylint: disable=too-many-branches
    # Ignored fuzz exceptions

    # Contract call exceptions
    if isinstance(exc, PypechainCallException):
        orig_exception = exc.orig_exception
        if orig_exception is None:
            return False

        # Insufficient liquidity error
        if isinstance(orig_exception, ContractCustomError) and exc.decoded_error == "InsufficientLiquidity()":
            return True

        # Circuit breaker triggered error
        if isinstance(orig_exception, ContractCustomError) and exc.decoded_error == "CircuitBreakerTriggered()":
            return True

        # DistributeExcessIdle error
        if isinstance(orig_exception, ContractCustomError) and exc.decoded_error == "DistributeExcessIdleFailed()":
            return True

        # MinimumTransactionAmount error
        if isinstance(orig_exception, ContractCustomError) and exc.decoded_error == "MinimumTransactionAmount()":
            return True

        # DecreasedPresentValueWhenAddingLiquidity error
        if (
            isinstance(orig_exception, ContractCustomError)
            and exc.decoded_error == "DecreasedPresentValueWhenAddingLiquidity()"
        ):
            return True

        # Closing long results in fees exceeding long proceeds
        if len(exc.args) > 1 and "Closing the long results in fees exceeding long proceeds" in exc.args[0]:
            return True

        # # Status == 0
        # if (
        #     isinstance(orig_exception, FailedTransaction)
        #     and len(orig_exception.args) > 0
        #     and "Receipt has status of 0" in orig_exception.args[0]
        # ):
        #     return True

    return False


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

    # We match the chain id of mainnet to do use the earliest block lookup, since
    # the chain is originally a fork of mainnet.
    chain = LocalChain(fork_uri=rpc_uri, config=LocalChain.Config(chain_id=1))

    hyperdrive_address = os.getenv("HYPERDRIVE_ADDRESS", None)
    if hyperdrive_address is None:
        raise ValueError("HYPERDRIVE_ADDRESS is not set")

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

    keeper_account: LocalAccount = Account().from_key(private_key)

    keeper_contract = IEverlongStrategyKeeperContract.factory(w3=chain._web3)(
        chain._web3.to_checksum_address(keeper_contract_address)
    )

    # Set up fuzzing environment
    hyperdrive_pool = LocalHyperdrive(chain, hyperdrive_address=hyperdrive_address, deploy=False)

    # Ensure all whale account addresses are checksum addresses
    # TODO abstract this out to run_fuzz_bots
    whale_accounts = {
        Web3.to_checksum_address(key): Web3.to_checksum_address(value) for key, value in MAINNET_WHALE_ADDRESSES.items()
    }

    agents = None

    while True:
        logging.info("Running fuzz bots...")

        agents = run_fuzz_bots(
            chain,
            hyperdrive_pools=[hyperdrive_pool],
            # We pass in the same agents when running fuzzing
            agents=agents,
            check_invariance=True,
            raise_error_on_failed_invariance_checks=True,
            raise_error_on_crash=True,
            log_to_rollbar=log_to_rollbar,
            ignore_raise_error_func=_fuzz_ignore_errors,
            random_advance_time=False,  # We take care of advancing time in the outer loop
            lp_share_price_test=False,
            base_budget_per_bot=FixedPoint(1_000_000),
            whale_accounts=whale_accounts,
            num_iterations=5,
            # Never refund agents
            minimum_avg_agent_base=FixedPoint(-1),
        )

        # TODO Random vault deposit and/or withdrawal

        # Execute keeper call
        execute_keeper_call_on_vaults(chain, keeper_account, keeper_contract)

        # TODO check vault invariance

        # Advance time for a day
        chain.advance_time(60 * 60 * 24)


class Args(NamedTuple):
    """Command line arguments for fuzzing everlong."""


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
    return Args()


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
    parser = argparse.ArgumentParser(description="Runs fuzzing everlong")

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
            _log_prefix = "Uncaught Critical Error in Fuzz Everlong:"
        else:
            _chain_name = _rpc_uri.split("//")[-1].split("/")[0]
            _log_prefix = f"Uncaught Critical Error for {_chain_name} in Fuzz Everlong:"
        log_rollbar_exception(exception=exc, log_level=logging.CRITICAL, rollbar_log_prefix=_log_prefix)
        raise exc
