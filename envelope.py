import envelope_pb2

white_envelope = envelope_pb2.White()
white_envelope.action = 'get_state'

blue_envelope = envelope_pb2.Blue()
blue_envelope.state = 'Starting'

red_envelope = envelope_pb2.Red()
red_envelope.type = 'Notification'
red_envelope.sender = '2.0.0.0.0'
red_envelope.toState = 'Running'

orange_envelope = envelope_pb2.Orange()
orange_envelope.type = 'Input'
orange_envelope.name = 'Start'
parameter = orange_envelope.parameters.chance_to_fail = 0.02

a = 0
