include .env
.PHONY: all build-types build-everlong

all:
	make build-everlong
	make build-types

build-everlong:
	cd ${EVERLONG_PATH} && make

build-types:
	pypechain --output-dir everlong_bot/everlong_types \
	${EVERLONG_PATH}/out/IAccountant.sol/ \
	${EVERLONG_PATH}/out/IAprOracle.sol/ \
	${EVERLONG_PATH}/out/IEverlongEvents.sol/ \
	${EVERLONG_PATH}/out/IEverlongStrategy.sol/ \
	${EVERLONG_PATH}/out/IEverlongStrategyKeeper.sol/ \
	${EVERLONG_PATH}/out/IPermissionedStrategy.sol/ \
	${EVERLONG_PATH}/out/IRoleManager.sol/ \
	${EVERLONG_PATH}/out/IRoleManagerFactory.sol/ \
	${EVERLONG_PATH}/out/IVault.sol/ \