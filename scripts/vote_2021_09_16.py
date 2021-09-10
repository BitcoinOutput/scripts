"""
Voting 16/09/2021.

1. Increase balancer reward program rate to 75000 LDO
2. Set balancer reward program allocations to 75000 LDO
"""

import time
from functools import partial
from typing import (
    Dict, Tuple,
    Optional
)

from brownie.utils import color
from brownie.network.transaction import TransactionReceipt

from utils.voting import create_vote
from utils.finance import encode_token_transfer
from utils.node_operators import (
    encode_set_node_operator_staking_limit
)
from utils.evm_script import (
    decode_evm_script,
    encode_call_script,
    calls_info_pretty_print
)
from utils.config import (
    prompt_bool,
    get_deployer_account,
    ldo_token_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
    lido_dao_agent_address,
    balancer_rewards_manager,
)

try:
    from brownie import interface
except ImportError:
    print(
        'You\'re probably running inside Brownie console. '
        'Please call:\n'
        'set_console_globals(interface=interface)'
    )


def set_console_globals(**kwargs):
    """Extract interface from brownie environment."""
    global interface
    interface = kwargs['interface']


def pp(text, value):
    """Pretty print with colorized."""
    print(text, color.highlight(str(value)), end='')


def make_ldo_payout(
        *not_specified,
        target_address: str,
        ldo_in_wei: int,
        reference: str,
        finance: interface.Finance
) -> Tuple[str, str]:
    """Encode LDO payout."""
    if not_specified:
        raise ValueError(
            'Please, specify all arguments with keywords.'
        )

    return encode_token_transfer(
        token_address=ldo_token_address,
        recipient=target_address,
        amount=ldo_in_wei,
        reference=reference,
        finance=finance
    )


def encode_set_balancer_rewards_rate(rate, manager, agent):
    return (
      agent.address,
      agent.forward.encode_input(
        encode_call_script([(manager.address,
        manager.set_rewards_limit_per_period.encode_input(
            rate
        ))])
      )
    )


def encode_set_balancer_allocations_amount(amount, manager, agent):
    return (
      agent.address,
      agent.forward.encode_input(
        encode_call_script([(manager.address,
        manager.set_allocations_limit.encode_input(
            amount
        ))])
      )
    )


def start_vote(
        tx_params: Dict[str, str],
        silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    # Lido contracts and constants:
    registry = interface.NodeOperatorsRegistry(
        lido_dao_node_operators_registry
    )
    finance = interface.Finance(lido_dao_finance_address)
    agent = interface.Agent(lido_dao_agent_address)
    balancerManager = interface.BalancerReawardsManager(balancer_rewards_manager)
    voting = interface.Voting(lido_dao_voting_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

    # Vote specific addresses and constants:
    # 1. Increase balancer reward program rate to 75000 LDO.
    balancer_rate = {
        'rate': 75000 * 10**18
    }
    # 2. Set balancer reward program allocations to 75000 LDO.
    balancer_allocations = {
        'rate': 75000 * 10**18
    }
    _set_allocations_rate_for_balancer_rewards_manager = encode_set_balancer_rewards_rate(
        balancer_rate['rate'],
        manager=balancerManager,
        agent=agent,
    )
    _set_allocations_amount_for_balancer_rewards_manager = encode_set_balancer_allocations_amount(
        balancer_allocations['rate'],
        manager=balancerManager,
        agent=agent,
    )

    # Encoding vote scripts:
    encoded_call_script = encode_call_script([
        _set_allocations_rate_for_balancer_rewards_manager,
        _set_allocations_amount_for_balancer_rewards_manager
    ])
    human_readable_script = decode_evm_script(
        encoded_call_script, verbose=False,
        specific_net='mainnet', repeat_is_error=True
    )

    # Show detailed description of prepared voting.
    if not silent:
        print(f'\n{__doc__}\n')

        pp('Lido finance contract at:', finance.address)
        pp('Lido node operator registry at:', registry.address)
        pp('Lido voting contract at:', voting.address)
        pp('Lido token manager at:', token_manager.address)
        pp('LDO token at:', ldo_token_address)

        print('\nPoints of voting:')
        total = len(human_readable_script)
        print(human_readable_script)
        for ind, call in enumerate(human_readable_script):
            print(f'Point #{ind + 1}/{total}.')
            print(calls_info_pretty_print(call))
            print('---------------------------')

        print('Does it look good?')
        resume = prompt_bool()
        while resume is None:
            resume = prompt_bool()

        if not resume:
            print('Exit without running.')
            return -1, None

    return create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=(
            'Omnibus vote: '
            '1) Increase balancer reward program rate to 75000 LDO, '
            '2) Set balancer reward program allocations to 75000 LDO, '
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'gas_price': '100 gwei'
    })
    print(f'Vote created: {vote_id}.')
    time.sleep(5)  # hack for waiting thread #2.
