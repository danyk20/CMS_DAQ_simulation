import string
from enum import Enum

from utils import compute_hierarchy_level


class State(Enum):
    Stopped = 0
    Starting = 1
    Running = 2
    Error = 3


class NodeAddress:

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

    def __init__(self, address: NodeAddress, parent: NodeAddress = None):
        self.state: State = State.Stopped
        self.level: int = compute_hierarchy_level(parent.get_port())
        self.address: NodeAddress = address
        self.parent: NodeAddress | None = parent
        self.children: dict[NodeAddress, [State]] = dict()
        self.chance_to_fail: float = 0
        self.build()

    def set_chance_to_fail(self, chance: float):
        self.chance_to_fail = chance

    def set_state(self, new_state: State):
        self.state = new_state

    def add_child(self):
        child_number: int = len(self.children) + 1
        child_level: int = self.level + 1
        child_offset: int = child_number * (10 ** (Node.MAXIMUM_DEPTH - child_level))
        child_port: int = int(self.address.get_port()) + child_offset
        child_address: NodeAddress = NodeAddress(self.address.get_ip() + ':' + str(child_port))
        self.children[child_address] = []

    def build(self):
        """
        Recursively build whole hierarchy of nodes based on Node.depth and Node.arity from root node.

        :return: None
        """
        while self.level < Node.depth and len(self.children) < Node.arity:
            self.add_child()
