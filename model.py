import asyncio
import string
from datetime import datetime
from enum import Enum
import random
from subprocess import Popen

from client import post_stop, post_start, post_notification
from utils import compute_hierarchy_level, get_configuration

configuration: dict[str, str | dict[str, str | dict]] = get_configuration()


class State(Enum):
    """
    Enum to represent Node states
    """
    Stopped = 0
    Starting = 1
    Running = 2
    Error = 3


class NodeAddress:
    """
    Class representing node address consisting of IP address and port in following format: 127.0.0.1:20000
    """

    def __init__(self, address: string):
        self.address = address

    def get_ip(self) -> string:
        if self.address:
            return self.address.split(':')[0]
        else:
            return None

    def get_port(self) -> string:
        if self.address:
            return self.address.split(':')[1]
        else:
            return None

    def get_full_address(self) -> string:
        return self.address

    def __eq__(self, other):
        return self.address == other.address

    def __hash__(self):
        return hash(self.address)

    def __ne__(self, other):
        return not (self == other)


class Node:
    """
    Representation of one Node in the hierarchy.

    MAXIMUM_DEPTH number of hierarchies that cannot be exceeded otherwise the script will crash, it can't be changed
    depth configuration number from range [0-4] referring to number of hierarchies
    arity configuration number from range [1-9] referring to number of children than each node except the leaves has
    """
    MAXIMUM_DEPTH = 4
    depth: int
    arity: int

    def __init__(self, address: NodeAddress):
        self.state: State = State.Stopped
        self.level: int = compute_hierarchy_level(address.get_port())
        self.address: NodeAddress = address
        self.children: dict[NodeAddress, [State]] = dict()
        self.started_processes: [Popen] = []
        self.chance_to_fail: float = 0
        self.debug_mode: bool = False
        self.build()

    async def set_state(self, new_state: State, probability_to_fail: float = 0,
                        debug: bool = False, transition_time: int = 0) -> None:
        if new_state == State.Running:
            self.chance_to_fail = float(probability_to_fail)
            self.debug_mode = debug
            await asyncio.sleep(transition_time)

            if len(self.children):
                # propagate to children
                for child_address in self.children:
                    asyncio.create_task(post_start(str(probability_to_fail), child_address.get_full_address(), debug))

            else:
                # change own state
                if float(probability_to_fail) > random.uniform(0, 1):
                    self.state = State.Error
                else:
                    self.state = State.Running
                    await post_notification(receiver_address=self.get_parent().get_full_address(),
                                            state=str(self.state),
                                            sender_address=self.address.get_full_address())
                    asyncio.create_task(self.run())

            if debug:
                now = datetime.now()
                print(
                    "Node " + self.address.get_port() + " is in " + str(self.state) + " at" + now.strftime(" %H:%M:%S"))
        elif new_state == State.Stopped:
            if len(self.children):
                # propagate to children
                for child_address in self.children:
                    print(self.address.get_port() + ' is sending stop to ' + child_address.get_port())
                    asyncio.create_task(post_stop(child_address.get_full_address(), debug))

            else:
                self.state = State.Stopped
                await post_notification(receiver_address=self.get_parent().get_full_address(), state=str(self.state),
                                        sender_address=self.address.get_full_address())

    def add_child(self) -> None:
        """
        Creates new child for the current node

        :return: None
        """
        child_number: int = len(self.children) + 1
        child_level: int = self.level + 1
        child_offset: int = child_number * (10 ** (Node.MAXIMUM_DEPTH - child_level))
        child_port: int = int(self.address.get_port()) + child_offset
        child_address: NodeAddress = NodeAddress(self.address.get_ip() + ':' + str(child_port))
        self.children[child_address] = []

    def build(self) -> None:
        """
        Recursively build whole hierarchy of nodes based on Node.depth and Node.arity from root node.

        :return: None
        """
        while self.level < Node.depth and len(self.children) < Node.arity:
            self.add_child()

    def update_state(self) -> None:
        """
        Update own state based on received notifications from the children with following rules:
        At least 1 child in error state -> error
        At least 1 child in stopped state -> stopped
        At least 1 child in starting state -> starting
        All children in running state -> running

        :return: None
        """
        stopped: int = 0
        starting: int = 0
        running: int = 0
        error: int = 0
        for child in self.children:
            child_status_list = self.children[child]
            if not child_status_list or child_status_list[-1] == State.Stopped:
                stopped += 1
            elif child_status_list[-1] == State.Starting:
                starting += 1
            elif child_status_list[-1] == State.Running:
                running += 1
            elif child_status_list[-1] == State.Error:
                error += 1
        if error:
            self.state = State.Error
        elif stopped:
            self.state = State.Stopped
        elif starting:
            self.state = State.Starting
        elif running == len(self.children):
            if self.state == State.Starting:
                asyncio.create_task(self.run())
            self.state = State.Running

    async def run(self) -> None:
        """
        Running loop while node is in running state it attempts to change to Error state with probability chance_to_fail

        :return: None
        """
        while self.state == State.Running:
            await asyncio.sleep(configuration['node']['time']['running'])
            if self.chance_to_fail > random.uniform(0, 1):
                self.state = State.Error
                await post_notification(receiver_address=self.get_parent().get_full_address(),
                                        state=str(self.state), sender_address=self.address.get_full_address())
                if self.debug_mode:
                    print('Changing State')
            if self.debug_mode:
                print(self.address.get_port() + ' -> ' + str(self.state))

    def get_parent(self) -> NodeAddress:
        """
        Compute parent node address based on current node port

        :return: NodeAddress of the parent
        """
        port = self.address.get_port()
        level = 4 - port.count('0')
        if level == 0:
            return NodeAddress(None)
        parent_port = list(port)
        parent_port[level] = '0'
        parent_port = ''.join(parent_port)
        return NodeAddress(self.address.get_ip() + ':' + parent_port)
