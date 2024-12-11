.PHONY: build-types

build-types:
	pypechain --output-dir everlong_bot/everlong_types \
	../everlong/out/IAccountant.sol/ \
	../everlong/out/IAprOracle.sol/ \
	../everlong/out/IEverlongEvents.sol/ \
	../everlong/out/IEverlongStrategy.sol/ \
	../everlong/out/IEverlongStrategyKeeper.sol/ \
	../everlong/out/IPermissionedStrategy.sol/ \
	../everlong/out/IRoleManager.sol/ \
	../everlong/out/IRoleManagerFactory.sol/ \
	../everlong/out/IVault.sol/ \