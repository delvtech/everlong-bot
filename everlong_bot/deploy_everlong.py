import os
import shutil
import subprocess

from agent0 import LocalChain


def deploy_everlong(chain: LocalChain, hyperdrive_address: str, clean_dirs=True) -> None:
    rpc_uri = chain.rpc_uri
    everlong_path = os.getenv("EVERLONG_PATH", None)

    # Deploy scripts assumes these exist
    output_paths = [
        f"{everlong_path}/deploy/1/roleManagers/",
        f"{everlong_path}/deploy/1/keeperContracts/",
        f"{everlong_path}/deploy/1/strategies/",
        f"{everlong_path}/deploy/1/vaults/",
    ]

    if clean_dirs:
        for path in output_paths:
            shutil.rmtree(path, ignore_errors=True)
            os.makedirs(path, exist_ok=True)

    # Everlong path is the path to the local everlong repo
    if everlong_path is None:
        raise ValueError("EVERLONG_PATH is not set")

    # Deploy via deploy scripts in the everlong repo
    cmd = (
        "source .env && "
        f"cd {everlong_path} && "
        "forge script "
        "script/DeployRoleManager.s.sol "
        f"--rpc-url {rpc_uri} "
        "--broadcast"
    )
    out = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
    )

    if out.returncode != 0:
        raise Exception(out.stderr.decode("utf-8"))

    cmd = (
        "source .env && "
        f"cd {everlong_path} && "
        "forge script "
        "script/DeployEverlongStrategyKeeper.s.sol "
        f"--rpc-url {rpc_uri} "
        "--broadcast"
    )
    # Deploy strategy keeper
    out = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
    )

    if out.returncode != 0:
        raise Exception(out.stderr.decode("utf-8"))

    # Deploy 2 everlong strategies and vaults
    for i in range(2):
        cmd = (
            "source .env && "
            f"cd {everlong_path} && "
            f"NAME='everlong_strategy_{i}' "
            f"HYPERDRIVE='{hyperdrive_address}' "
            "forge script "
            "script/DeployEverlongStrategy.s.sol "
            f"--rpc-url {rpc_uri} "
            "--broadcast"
        )
        out = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
        )

        if out.returncode != 0:
            raise Exception(out.stderr.decode("utf-8"))

    for i in range(2):
        cmd = (
            "source .env && "
            f"cd {everlong_path} && "
            f"STRATEGY_NAME='everlong_strategy_{i}' "
            f"NAME='vault_{i}' "
            f"SYMBOL='{'V' * i}' "
            "CATEGORY=0 "
            "forge script "
            "script/DeployVault.s.sol "
            f"--rpc-url {rpc_uri} "
            "--broadcast"
        )
        out = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
        )

        if out.returncode != 0:
            raise Exception(out.stderr.decode("utf-8"))

    pass
