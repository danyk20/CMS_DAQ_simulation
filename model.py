import asyncio
import json
import time
from datetime import datetime
from enum import Enum
import random
from subprocess import Popen
import pika

import send
import client
import utils

configuration: dict[str, str | dict[str, str | dict]] = utils.get_configuration()


class State(Enum):
    """
    Enum to represent Node states
    """
    Initialisation = 0
    Stopped = 1
    Starting = 2
    Running = 3
    Error = 4


class NodeAddress:
    """
    Class representing node address consisting of IP address and port in following format: 127.0.0.1:20000
    """

    def __init__(self, address: str | None):
        self.address = address

    def get_ip(self) -> str | None:
        if self.address:
            return self.address.split(':')[0]
        else:
            return None

    def get_port(self) -> str | None:
        if self.address:
            return self.address.split(':')[1]
        else:
            return None

    def get_full_address(self) -> str:
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
    MAXIMUM_DEPTH = configuration['node']['depth']['max'] - 1  # maximum achievable depth
    depth: int
    arity: int

    def __init__(self, address: NodeAddress):
        self.state: State = State.Initialisation
        self.level: int = utils.compute_hierarchy_level(address.get_port())
        self.address: NodeAddress = address
        self.children: dict[NodeAddress, [State]] = dict()
        self.started_processes: [Popen] = []
        self.chance_to_fail: float = 0
        self.build()
        self.kill_rpc_serer = None
        self.kill_consumer = None

    async def set_state(self, new_state: State, probability_to_fail: float = 0, transition_time: int = 0) -> None:
        """
        Change state from current to new state or fail.

        :param new_state:
        :param probability_to_fail: percentage value between 0 and 1
        :param transition_time: how long should transition last
        :return: None
        """
        if configuration['debug'] == 'True':
            now = datetime.now()
            print(
                "Node " + self.address.get_port() + " is in " + str(self.state) + " at" + now.strftime(" %H:%M:%S"))
        if new_state == State.Running:
            self.chance_to_fail = float(probability_to_fail)
            await asyncio.sleep(transition_time)

            if len(self.children):
                asyncio.get_running_loop().create_task(self.send_to_children(new_state))
            else:
                asyncio.get_running_loop().create_task(self.enter_running_state())

        elif new_state == State.Stopped:
            if len(self.children):
                asyncio.get_running_loop().create_task(self.send_to_children(new_state))
            else:
                self.state = State.Stopped
                asyncio.get_running_loop().create_task(self.notify_parent())

    async def enter_running_state(self) -> None:
        """
        Change state from Starting to Running

        :return: None
        """
        if float(self.chance_to_fail) > random.uniform(0, 1):
            self.state = State.Error
        else:
            self.state = State.Running
            asyncio.get_running_loop().create_task(self.notify_parent())
            asyncio.get_running_loop().create_task(self.run())
        if configuration['debug'] == 'True':
            now = datetime.now()
            print(
                "Node " + self.address.get_port() + " is in " + str(self.state) + " at" + now.strftime(
                    " %H:%M:%S"))

    async def send_to_children(self, new_state: State) -> None:
        """
        Propagate received message to all children

        :param new_state: propagated state
        :return: None
        """
        for child_address in self.children:
            if configuration['debug'] == 'True':
                print(self.address.get_port() + ' is sending ' + str(new_state) + ' to ' + child_address.get_port())
            if configuration['architecture'] == 'MOM':
                routing_key = utils.get_bounding_key(child_address.get_port())
                message = str(new_state)
                send.post_state_change(message, routing_key, self.chance_to_fail)
            else:
                if new_state == State.Running:
                    asyncio.create_task(
                        client.post_start(str(self.chance_to_fail), child_address.get_full_address()))
                elif new_state == State.Stopped:
                    asyncio.create_task(client.post_stop(child_address.get_full_address()))

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
        initialisation = 0
        stopped: int = 0
        starting: int = 0
        running: int = 0
        error: int = 0
        for child in self.children:
            child_status_list = self.children[child]
            if not child_status_list:
                initialisation += 1
            elif child_status_list[-1] == State.Stopped:
                stopped += 1
            elif child_status_list[-1] == State.Starting:
                starting += 1
            elif child_status_list[-1] == State.Running:
                running += 1
            elif child_status_list[-1] == State.Error:
                error += 1
        if error:
            self.state = State.Error
        elif initialisation:
            self.state = State.Initialisation
        elif stopped:
            self.state = State.Stopped
        elif starting:
            self.state = State.Starting
        elif running == len(self.children):
            if self.state != State.Running:
                self.state = State.Running
                asyncio.get_running_loop().create_task(self.run())
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
                await self.notify_parent()
                if configuration['debug'] == 'True':
                    print('Changing State')
            if configuration['debug'] == 'True':
                print(self.address.get_port() + ' -> ' + str(self.state))

    async def notify_parent(self):
        """
        Notify parent about current state based on selected architecture in  configuration.yaml

        :return: None
        """
        if configuration['architecture'] == 'MOM':
            routing_key = utils.get_bounding_key(self.get_parent().get_port())
            sender_id = utils.get_bounding_key(self.address.get_port())
            send.post_state_notification(current_state=str(self.state),
                                         routing_key=routing_key,
                                         sender_id=sender_id)
        else:
            # REST
            await client.post_notification(receiver_address=self.get_parent().get_full_address(),
                                           state=str(self.state), sender_address=self.address.get_full_address())

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

    def run_get_server(self) -> None:
        """
        Run rpc server to respond on get_state requests

        :return: None
        """

        def stop():
            """Stop listening for jobs"""
            connection.add_callback_threadsafe(_stop)

        def _stop():
            channel.stop_consuming()
            channel.close()
            connection.close()

        def get_current_state() -> str:
            time.sleep(configuration['node']['time']['get'])
            return str(self.state).split('.')[-1]

        def on_request(ch, method, props, body) -> None:
            """
            Triggered when there is message in <queue_name>, and reply to it by sending get_current_state() return value

            :param ch:
            :param method:
            :param props:
            :param body:
            :return:
            """
            if json.loads(body)['action'] == 'get_state':
                response = utils.get_blue_envelope(get_current_state())
                print('Returning current state: ' + response + ' of node ' + self.address.get_port())
                ch.basic_publish(exchange='',
                                 routing_key=props.reply_to,
                                 properties=pika.BasicProperties(correlation_id=props.correlation_id),
                                 body=json.dumps(response))
                ch.basic_ack(delivery_tag=method.delivery_tag)

        queue_name = 'rpc_queue:' + utils.get_bounding_key(self.address.get_port())

        connection = pika.BlockingConnection(pika.ConnectionParameters(host=configuration['URL']['address']))

        channel = connection.channel()

        channel.queue_declare(queue=queue_name, auto_delete=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=queue_name, on_message_callback=on_request)

        if configuration['debug']:
            print(" [x] Awaiting RPC requests " + self.address.get_port())
        self.kill_rpc_serer = stop
        channel.start_consuming()
