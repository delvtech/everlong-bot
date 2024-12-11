import logging

from agent0 import Chain
from eth_account.signers.local import LocalAccount

from everlong_bot.everlong_types import IEverlongStrategyKeeperContract, IRoleManagerContract, IVaultContract
from everlong_bot.everlong_types.IEverlongStrategy import TendConfig


def execute_keeper_call(
    keeper_contract: IEverlongStrategyKeeperContract,
    sender: LocalAccount,
    vault_addr: str,
    strategy_addr: str,
):
    # TODO update tend config with sane parameters
    tend_config = TendConfig(
        minOutput=0,
        minVaultSharePrice=0,
        positionClosureLimit=0,
        extraData=b"",
    )

    # Update debt
    if keeper_contract.functions.shouldUpdateDebt(_vault=vault_addr, _strategy=strategy_addr).call():
        # TODO implement rollbar logging
        logging.info("Calling updateDebt")
        # Calling function first for debugging
        function = keeper_contract.functions.update_debt(_vault=vault_addr, _strategy=strategy_addr)
        function.call(transaction={"from": sender.address})
        function.sign_transact_and_wait(sender, validate_transaction=True)

    # Tend
    if keeper_contract.functions.shouldTend(_strategy=strategy_addr).call():
        logging.info("Calling tend")
        function = keeper_contract.functions.tend(_strategy=strategy_addr, _config=tend_config)
        function.call(transaction={"from": sender.address})
        function.sign_transact_and_wait(sender, validate_transaction=True)

    # Strategy report
    if keeper_contract.functions.shouldStrategyReport(_strategy=strategy_addr).call():
        logging.info("Calling strategyReport")
        function = keeper_contract.functions.strategyReport(_strategy=strategy_addr, _config=tend_config)
        function.call(transaction={"from": sender.address})
        function.sign_transact_and_wait(sender, validate_transaction=True)

    # Process report
    if keeper_contract.functions.shouldProcessReport(_vault=vault_addr, _strategy=strategy_addr).call():
        logging.info("Calling processReport")
        function = keeper_contract.functions.processReport(_vault=vault_addr, _strategy=strategy_addr)
        function.call(transaction={"from": sender.address})
        function.sign_transact_and_wait(sender, validate_transaction=True)


def get_all_vaults_from_keeper(chain: Chain, keeper_contract: IEverlongStrategyKeeperContract) -> list[IVaultContract]:
    # TODO do these ever change? If not, we can likely abstract this outside of the periodic calls.
    role_manager_addr = keeper_contract.functions.roleManager().call()
    role_manager_contract = IRoleManagerContract.factory(w3=chain._web3)(
        # TODO do the conversion in the underlying pypechain library
        chain._web3.to_checksum_address(role_manager_addr)
    )

    # Get all vaults
    out = []
    vault_addrs = role_manager_contract.functions.getAllVaults().call()
    for vault_addr in vault_addrs:
        out.append(IVaultContract.factory(w3=chain._web3)(chain._web3.to_checksum_address(vault_addr)))
    return out


def execute_keeper_call_on_vaults(chain: Chain, sender: LocalAccount, keeper_contract: IEverlongStrategyKeeperContract):
    vaults = get_all_vaults_from_keeper(chain, keeper_contract)

    for vault_contract in vaults:
        strategy_addr = vault_contract.functions.default_queue(0).call()

        execute_keeper_call(keeper_contract, sender, vault_contract.address, strategy_addr)
