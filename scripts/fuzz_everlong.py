"""Bots for fuzzing the everlong vault, keeper, and the underlying hyperdrive pool.

This script launches a local anvil chain forked off of mainnet, and runs
random trades on the hyperdrive pool and everlong vault, as well as running necessary
keeper functions for vault maintenance.
"""

from __future__ import annotations

import argparse
import logging
import os
import random
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

from everlong_bot.deploy_everlong import deploy_everlong
from everlong_bot.everlong_types import IEverlongStrategyKeeperContract, IVaultContract
from everlong_bot.keeper_bot import execute_keeper_call_on_vaults, get_all_vaults_from_keeper

# Defines the whale addresses to fund the bots with
DAI_ADDRESS = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
MAINNET_WHALE_ADDRESSES = {
    # DAI
    DAI_ADDRESS: "0xf6e72Db5454dd049d0788e411b06CfAF16853042",
}


def _fuzz_ignore_errors(exc: Exception) -> bool:
    """Function defining errors to ignore during fuzzing of hyperdrive pools."""
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
    """Runs the everlong fuzzing.

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
    keeper_contract_address = None
    rpc_uri = os.getenv("MAINNET_RPC_URI", None)
    if rpc_uri is None:
        raise ValueError("MAINNET_RPC_URI is not set")

    hyperdrive_address = os.getenv("HYPERDRIVE_ADDRESS", None)
    if hyperdrive_address is None:
        raise ValueError("HYPERDRIVE_ADDRESS is not set")

    private_key = os.getenv("KEEPER_PRIVATE_KEY", None)
    if private_key is None:
        raise ValueError("KEEPER_PRIVATE_KEY is not set")

    # Set up objects
    # Get chain
    chain = LocalChain(fork_uri=rpc_uri, config=LocalChain.Config())

    # Set up hyperdrive pool object needed by agent0 fuzzing
    hyperdrive_pool = LocalHyperdrive(chain, hyperdrive_address=hyperdrive_address, deploy=False)

    # Set up keeper account
    keeper_account: LocalAccount = Account().from_key(private_key)

    # Deploy everlong
    keeper_contract_address = deploy_everlong(chain, hyperdrive_address=hyperdrive_address, num_vaults=2)

    # Set up keeper contract pypechain object
    keeper_contract = IEverlongStrategyKeeperContract.factory(w3=chain._web3)(
        chain._web3.to_checksum_address(keeper_contract_address)
    )
    # Query all vaults from the keeper
    vaults = get_all_vaults_from_keeper(chain, keeper_contract)

    # Ensure all whale account addresses are checksum addresses
    # TODO abstract this out to run_fuzz_bots
    whale_accounts = {
        Web3.to_checksum_address(key): Web3.to_checksum_address(value) for key, value in MAINNET_WHALE_ADDRESSES.items()
    }

    # Shortcut variables
    base_token_contract = hyperdrive_pool.interface.base_token_contract
    agents = None
    assert chain.config.rng is not None

    # Run fuzzing
    while True:
        logging.info("Running fuzz bots...")

        # Run fuzzing via agent0 function on underlying hyperdrive pool.
        # By default, this sets up 4 agents.
        # `check_invariance` also runs the pool's invariance checks after trades.
        # We only run for 1 iteration here, as we want to make additional random trades
        # wrt everlong.
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
            num_iterations=1,
            # Never refund agents
            minimum_avg_agent_base=FixedPoint(-1),
        )

        # Run random vault deposit and/or withdrawal
        for agent in agents:
            # Pick a vault at random
            # numpy rng has type issues with lists
            vault: IVaultContract = chain.config.rng.choice(vaults)  # type: ignore
            # Type narrowing
            assert isinstance(vault, IVaultContract)

            # Deposit or withdraw
            trade = chain.config.rng.choice(["deposit", "redeem"])  # type: ignore
            match trade:
                case "deposit":
                    balance = base_token_contract.functions.balanceOf(agent.address).call()
                    if balance > 0:
                        # TODO can't use numpy rng since it doesn't support uint256.
                        # Need to use the state from the chain config to use the same rng object.
                        amount = random.randint(0, balance)
                        logging.info(f"Agent {agent.address} is depositing {amount} to {vault.address}")
                        # Approve amount to vault
                        base_token_contract.functions.approve(
                            spender=vault.address, amount=amount
                        ).sign_transact_and_wait(account=agent.account, validate_transaction=True)
                        # Deposit amount to vault
                        vault.functions.deposit(assets=amount, receiver=agent.address).sign_transact_and_wait(
                            account=agent.account, validate_transaction=True
                        )
                case "redeem":
                    balance = vault.functions.balanceOf(agent.address).call()
                    if balance > 0:
                        amount = random.randint(0, balance)
                        logging.info(f"Agent {agent.address} is redeeming {amount} from {vault.address}")
                        vault.functions.redeem(
                            shares=amount, receiver=agent.address, owner=agent.address
                        ).sign_transact_and_wait(account=agent.account, validate_transaction=True)

        # Execute keeper calls for vault maintenance
        execute_keeper_call_on_vaults(chain, keeper_account, keeper_contract)

        # TODO check vault invariance

        # Advance time for a day
        # TODO parameterize the amount of time to advance.
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


# Run fuzing
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
