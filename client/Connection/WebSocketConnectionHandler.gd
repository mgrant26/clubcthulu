extends Node

@onready var ConnectionHandler = get_node("/root/ConnectionHandler")

var client: WebSocketPeer
var thread: Thread
var open = false
# Called when the node enters the scene tree for the first time.
func _ready():
	if not OS.get_name() == "Web":
		return
	client = WebSocketPeer.new()
	client.connect_to_url("ws://localhost:25555")
	
	thread = Thread.new()
	thread.start(_thread)

func send(message):
	client.send(message)

func _thread():
	if client == null:
		return
	var state = client.get_ready_state()
	while state != WebSocketPeer.STATE_CLOSED:
		state = client.get_ready_state()
		client.poll()
		if state == WebSocketPeer.STATE_OPEN:
			if open == false:
				open = true
				var to_send = JSON.stringify(ConnectionHandler.public_key_request)
				client.send(to_send.to_utf8_buffer())
			while client.get_available_packet_count():
				var packet = client.get_packet()
				var json = JSON.new()
				# Uses the JSON objects parse method to parse packet information and convert it into a Dictionary
				var res = json.parse(packet.get_string_from_utf8())
				if res == OK:
					# Locks the mutex
					ConnectionHandler.mutex.lock()

					#Appends the Dictionary tot he queue
					ConnectionHandler.message_queue.append(json.data)

					# Unlocks the mutex
					ConnectionHandler.mutex.unlock()
		elif state == WebSocketPeer.STATE_CONNECTING:
			print("Connecting...")
		elif state == WebSocketPeer.STATE_CLOSING:
			pass
	open = false

func _notification(note):
	if (note == NOTIFICATION_PREDELETE && OS.get_name() == "Web"):
		print("Killing WebSocket Thread")
		client.close()
		if thread != null:
			thread.wait_to_finish()
