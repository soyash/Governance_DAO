from brownie import (
    GovernorContract,
    GovernanceToken,
    GovernanceTimeLock,
    Box,
    Contract,
    config,
    network,
    accounts,
    chain,
)
from web3 import Web3, constants
import time

# Governor Contract
QUORUM_PERCENTAGE = 4
VOTING_PERIOD = 5  # 5 blocks VOTING_PERIOD = 45818  => 1 week - more traditional. 
VOTING_DELAY = 1  # 1 block

# Timelock
# MIN_DELAY = 3600  # 1 hour - more traditional
MIN_DELAY = 1  # 1 seconds

# Proposal
PROPOSAL_DESCRIPTION = "Proposal #1: Store 1 in the Box!"
NEW_STORE_VALUE = 5

# Step 1:
def deploy_governor():
    account = accounts[0]

    # Deploying governance token first
    governance_token = GovernanceToken.deploy({'from':account})
    # delegating max supply of token to ourselves this happens automatically when we transfer tokens but manually when minted
    governance_token.delegate(account, {'from': account})
    print(f"Checkpoints: {governance_token.numCheckpoints(account)}")

    # Deploying Time Lock
    governance_time_lock = GovernanceTimeLock.deploy(MIN_DELAY, [], [], {'from':account})

    # Deploying Governor Contract
    governor = GovernorContract.deploy(governance_token.address, governance_time_lock.address, QUORUM_PERCENTAGE, VOTING_PERIOD, VOTING_DELAY, {'from': account})

    # Setting roles
    proposer_role = governance_time_lock.PROPOSER_ROLE()
    executor_role = governance_time_lock.EXECUTOR_ROLE()
    timelock_admin_role = governance_time_lock.TIMELOCK_ADMIN_ROLE()
    governance_time_lock.grantRole(proposer_role, governor, {"from": account})
    governance_time_lock.grantRole(executor_role, constants.ADDRESS_ZERO, {"from": account}) # ADDRESS_ZERO means anyone can be executor
    tx = governance_time_lock.revokeRole(timelock_admin_role, account, {"from": account}) # revoking role from self
    tx.wait(1)


# Step 2:
def deploy_box_to_be_governed():
    account = accounts[0]
    box = Box.deploy({"from": account})
    tx = box.transferOwnership(GovernanceTimeLock[-1], {"from": account})
    tx.wait(1)    


def propose(store_value):
    account = accounts[0]
    args = (store_value,)
    # Dont know how this works
    encoded_function = Contract.from_abi("Box", Box[-1], Box.abi).store.encode_input(
        *args
    )
    print(encoded_function)

    propose_tx = GovernorContract[-1].propose(
        [Box[-1].address],
        [0],
        [encoded_function],
        PROPOSAL_DESCRIPTION,
        {"from": account},
    )

    tx = account.transfer(accounts[0], "0 ether")
    tx.wait(1)

    propose_tx.wait(2)  # We wait 2 blocks to include the voting delay
    # This will return the proposal ID, brownie.exceptions.EventLookupError will be 
    # thrown if ProposalCreated event is not emitted.
    proposal_id = propose_tx.events['ProposalCreated']['proposalId'] # you could also do `propose_tx.return_value` if your node allows
    print(f"Proposal state {GovernorContract[-1].state(proposal_id)}")
    print(
        f"Proposal snapshot {GovernorContract[-1].proposalSnapshot(proposal_id)}"
    )
    print(
        f"Proposal deadline {GovernorContract[-1].proposalDeadline(proposal_id)}"
    )
    return proposal_id


def main():
    deploy_governor()
    deploy_box_to_be_governed()
    proposal_id = propose(NEW_STORE_VALUE)
    print(f"Proposal ID {proposal_id}")