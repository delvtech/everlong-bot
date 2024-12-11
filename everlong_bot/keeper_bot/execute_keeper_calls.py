from agent0 import Chain
from eth_account.signers.local import LocalAccount

from everlong_bot.everlong_types import (
    IEverlongStrategyKeeperContract,
    IRoleManagerContract,
    IVaultContract,
)


def execute_keeper_calls(
    chain: Chain, sender: LocalAccount, keeper_contract: IEverlongStrategyKeeperContract
):

    # TODO do these ever change? If not, we can likely abstract this outside of the periodic calls.
    role_manager_addr = keeper_contract.functions.roleManager().call()
    role_manager_contract = IRoleManagerContract.factory(w3=chain._web3)(
        chain._web3.to_checksum_address(role_manager_addr)
    )

    # Get all vaults
    vaults = role_manager_contract.functions.getAllVaults().call()

    pass
