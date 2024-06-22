extends Node

@onready var WebSocketConnectionHandler = get_node("/root/WebSocketConnectionHandler")

var UDP : PacketPeerUDP = PacketPeerUDP.new()

# The request for the public key sent to the server
const public_key_request = {
	"request": "obtain-public"
}
# Whether or not the client is connected
var connected = false

# Whether or not the client is currently attempting to connect
var connecting = false

var moving = false

var accept_player_input = true

# Initializes Crypto functions
var crypto = Crypto.new()
var crypto_public = CryptoKey.new()

var ForeignPlayer = preload("res://Player/foreign_player.gd")
var Player = preload("res://Player/player.tscn")

var players = {}

# The session id
var session_id: String = ""
var user_name: String = ""
var user_id: String = ""
var player = null
var camera: Camera2D = null

var hostname = null

# The last error message sent from the server
var last_error_message = ""

# The thread for handling messages
var thread: Thread = null

# Mutex to prevent concurrent modifications of queues
var mutex: Mutex = null

# The message queue, holds all messages sent from the server before they are processed
var message_queue: Array = []
# Unused info queue, does nothing
var chat_queue: Array = []

var move_queue: Vector2 = Vector2.ZERO
var vel_queue: Vector2 = Vector2.ZERO

# Dialog box for popups
var dialog: AcceptDialog

var timer: Thread

var chunk_width = 0
var chunk_height = 0

var ChatHandler = null

## Called when the server is read
func _ready():
	# Initializes a new dialog box
	dialog = AcceptDialog.new()
	# Initializes a new mutex
	mutex = Mutex.new()
	# Adds dialog to this node's children so that it can be used on any scene
	add_child(dialog)
	print("Connection Handler ready!")

## Called constantly
func _process(_delta):
	if message_queue.size() == 0:
		return
	# Locks the mutex in order to prevent concurrent modification
	mutex.lock()
	var message_queue_copy = message_queue.duplicate(true)
	mutex.unlock()
	# Iterates through all of the messages in the message queue
	for data in message_queue_copy:
		# If the message does not contain a response variable it is not a valid server message
		if not data.has('response'):
			continue
		# Gets the response type from the message
		var response = data["response"]
		
		# Encodes the packet and sends it to the server
		#UDP.put_packet(res.to_utf8_buffer())
		
		#Changes functionality based on response values
		match response:
			# When an error response is recieved popup the error message
			"error":
				last_error_message = data.get("message")
				show_popup("Error", data.get("message"))
			# TODO: write message response stuff
			"message":
				chat_queue.append([data.get("origin"), data.get("message")])
			"client-update":
				var o_name = data.get("client-name")
				var id = data.get("client-id")
				if o_name.is_empty() or id.is_empty():# or id == user_id:
					continue
				var chunk_x = data.get("chunk-x")
				var chunk_y = data.get("chunk-y")
				var x = data.get("x") + (chunk_x * chunk_width)
				var y = data.get("y") + (chunk_y * chunk_height)
				if players.has(id):
					players.get(id).teleport(Vector2(x, y))
				else:
					add_player(o_name, id)
					var hold = players.get(id)
					hold.teleport(Vector2(x, y))
					if id == user_id:
						create_player()
			"client-joined":
				var o_name = data.get("client-name")
				var id = data.get("client-id")
				if o_name.is_empty() or id.is_empty():
					continue
				var tplayer = add_player(o_name, id)
				var chunk_x = data.get("chunk-x")
				var chunk_y = data.get("chunk-y")
				var x = int(data.get("x")) 
				var y = int(data.get("y"))
				x += (chunk_x * chunk_width)
				y += (chunk_y * chunk_height)
				players.get(id).teleport(Vector2(x, y))
				if id == user_id:
					create_player()
				if ChatHandler != null:
					ChatHandler.player_joined(tplayer)
			"client-left":
				var id = data.get("id")
				if id != null and players.has(id):
					#players[id].player_instance.queue_free()
					print("leaving")
					players[id].leave(get_node("/root/"))
					if ChatHandler != null:
						ChatHandler.player_left(players[id])
					players.erase(id)
			"position-update":
				var target = data.get("target")
				if !players.has(target):
					continue
					
				var loc_x = (chunk_width * data.get("new-chunk-x")) + data.get("new-x")
				var loc_y = (chunk_height * data.get("new-chunk-y")) + data.get("new-y")
				
				var pla = players.get(target)
				var time = data.get("timestamp")
				if pla.last_time < time:
					pla.last_time = time
					pla.teleport(Vector2(loc_x, loc_y))
				
			# When a success response is recieved respond based on type
			"success":
				var type = data["type"]
				match type:
					# Pulls the session data if type is login-success
					"login-success":
						load_session(data)
						getPlayers()
						chunk_width = data.get("chunk-width")
						chunk_height = data.get("chunk-height")
						
					# Shows a Success popup if type is register-success
					"register-success":
						show_popup("Success", "Successfully Registered!")
						get_tree().change_scene_to_file("res://Scenes/LoginScreen.tscn")
					# Shows a Success popup if type is logout-success
					"logout-success":
						show_popup("Success", "You are now logged out")
						kill_connection()
						#get_tree().change_scene_to_file("res://Scenes/DirectConnect.tscn")
			# Loads the provided public key if response is confirm-public
			"confirm-public":
				connecting = false
				load_public(data)
			# Shows a popup containing message if response is info
			"info":
				if data.has('type') && data.get('type') == 'kicked':
					print("Kicked.")
					kill_connection()
					show_popup("INFO", data['message'])
					#get_tree().change_scene_to_file("res://Scenes/DirectConnect.tscn")
	# Clears the message queue as everything has been proccessed
	mutex.lock()
	message_queue.clear()
	# Frees the mutex
	mutex.unlock()

## Attempts to connect to the supplied location
func connect_udp(ip, port) -> Error:
	if OS.get_name() == "Web":
		print("No udp on web")
		return FAILED
	# Creates a PacketPeerUDP object for connection
	UDP = PacketPeerUDP.new()
	# Creates a container for the public key
	crypto_public = CryptoKey.new()
	# Attempts t oconnect to the supplied ip and port
	hostname = IP.resolve_hostname(ip, IP.TYPE_ANY)
	var error = UDP.connect_to_host(hostname, port)
	print("Attempt")
	
	# Return FAILED and show a popup if the connection doesn't return OK
	if error != OK:
		show_popup("Error", "Connection Failed")
		print(error)
		return FAILED
	
	# Starts the message handling thread
	thread = Thread.new()
	
	# Starts the thread using _pull_information as its executable
	thread.start(_pull_information)
	
	#timer = Thread.new()
	#timer.start(_free_queue)
	
	# Converst public_key_request into a string and encodes it 
	var to_send = JSON.stringify(public_key_request)

	#Sends the request to the server
	sendPacket(to_send)
	
	#Returns OK
	return OK

func add_player(o_name, id):
	var fp = ForeignPlayer.new()
	fp.create(get_node("/root"), o_name, id)
	players[id] = fp
	return fp

## Attempts to load the public key from supplied Dictionary
func load_public(data: Dictionary):
	var public_key = data.get("public-key")
	if crypto_public.load_from_string(public_key, true) == OK:
		connected = true
	else:
		show_popup("An error occured.", "Something went wrong loading the public key.")

## Attempts to load session id from supplied Dictionary
func load_session(data: Dictionary):
	session_id = data.get("session")
	user_name = data.get("name")
	user_id = data.get("id")

## Attempts to login to the supplied user
func login(username: String, password: String) -> Error:
	if (UDP == null || !UDP.is_socket_connected()) && !WebSocketConnectionHandler.open:
		return FAILED

	# Encrypts the password with the public key
	var pc = crypto.encrypt(crypto_public, password.to_utf8_buffer())

	# Builds the session init packet
	var request = {
		"request": "init-session",
		"username": username,
		"password": Marshalls.raw_to_base64(pc)
	}
	
	# Converts the packet to a string and then encode it
	var to_send = JSON.stringify(request)

	# Sends the packet to the server
	sendPacket(to_send)
	
	# Returns OK
	return OK

func register(username: String, password: String, rptPassword: String):
	if (UDP == null || !UDP.is_socket_connected()) && !WebSocketConnectionHandler.open:
		return FAILED
		
	if (password != rptPassword):
		show_popup("Error", "Passwords are not the same.")
		return FAILED	
	
	var pc = crypto.encrypt(crypto_public, password.to_utf8_buffer())
	
	var request = {
		"request": "register",
		"username": username,
		"password": Marshalls.raw_to_base64(pc)
	}
	
	var to_send = JSON.stringify(request)
	
	sendPacket(to_send)
	
	return OK

func _free_queue():
	while UDP.is_socket_connected():
		if UDP == null:
			break
		if move_queue.length() > 0:
			move()

func queue_move(loc: Vector2, vel: Vector2):
	move_queue = loc
	vel_queue = vel

func move():
	if (UDP == null || !UDP.is_socket_connected()) && !WebSocketConnectionHandler.open:
		return FAILED
	if session_id.is_empty():
		return FAILED
	if vel_queue.length() == 0:
		return FAILED
	var request = {
		"request": "move",
		"session-id": session_id,
		"x": vel_queue.x,
		"y": vel_queue.y,
	}
	move_queue = Vector2.ZERO
	vel_queue = Vector2.ZERO
	var to_send = JSON.stringify(request)
	
	sendPacket(to_send)
	moving = true
	return OK

func end_move():
	if (UDP == null || !UDP.is_socket_connected()) && !WebSocketConnectionHandler.open:
		return FAILED
	if session_id.is_empty():
		return FAILED
	var request = {
		"request": "end-move",
		"session-id": session_id
	}
	move_queue = Vector2.ZERO
	vel_queue = Vector2.ZERO
	var to_send = JSON.stringify(request)
	
	sendPacket(to_send)
	moving = false
	return OK

## Attempts to log out of the server
func logout():
	if (UDP == null || !UDP.is_socket_connected()) && !WebSocketConnectionHandler.open:
		return
	if session_id.is_empty():
		return
	# Builds the end session packet
	var request = {
		"request": "end-session",
		"session-id": session_id
	}

	# Converts the packet into string and the encodes it
	var to_send = JSON.stringify(request)

	#sends the packet to the server
	sendPacket(to_send)
	session_id = ""
	user_name = ""
	user_id = ""
	

## Thread runnable to accept information from the server while connected
func _pull_information():
	# Loop while the socket is connected
	while UDP != null && UDP.is_socket_connected():
		# If there are packets to process process one
		if UDP.get_available_packet_count() > 0:
			# Gets the packet
			var packet = UDP.get_packet()
			# Gets the error 
			var error = UDP.get_packet_error()
			
			# If the error is anything other than OK skip
			if error != OK:
				continue
			
			# Creates a JSON object
			var json = JSON.new()
			# Uses the JSON objects parse method to parse packet information and convert it into a Dictionary
			var res = json.parse(packet.get_string_from_utf8())
			
			# If the result doesn't return an error
			if res == OK:
				# Locks the mutex
				mutex.lock()

				#Appends the Dictionary tot he queue
				message_queue.append(json.data)

				# Unlocks the mutex
				mutex.unlock()
	print("end")
	if !session_id.is_empty():
		logout()

func sendPacket(message: String):
	if WebSocketConnectionHandler.open:
		WebSocketConnectionHandler.send(message.to_utf8_buffer())
	elif UDP != null and UDP.is_socket_connected():
		UDP.put_packet(message.to_utf8_buffer())

## Attempts to send a message to the server
func sendMessage(message):
	# Builds the message packet
	var request = {
		"request": "message",
		"message": message,
		"session-id": session_id
	}
	
	var to_send = JSON.stringify(request)
	sendPacket(to_send)

func getPlayers():
	# Builds the message packet
	var request = {
		"request": "update",
		"session-id": session_id
	}
	
	var to_send = JSON.stringify(request)
	sendPacket(to_send)

## Attempts to kill the connection to the server
func kill_connection():
	if connected == false:
		return
	# Sets connected to false
	connected = false
	
	# logout just in case
	if !session_id.is_empty():
		logout()
		session_id = ""
	
	# Closes the connection in UDP
	
	if UDP != null and UDP.is_socket_connected():
		print("Killing UDP connection")
		var socket = PacketPeerUDP.new()
		socket.set_dest_address("127.0.0.1", UDP.get_local_port())
		socket.put_packet("e".to_utf8_buffer())
		socket.close()
		UDP.close()
	
	# Waits for the message thread to finish what it is doing
	print("Killing Message Thread")
	if thread != null:
		thread.wait_to_finish()
	print("Killing Timer")
	if timer != null:
		timer.wait_to_finish()
	if player != null:
		player.queue_free()
		player = null
	for pla in players:
		var k = players[pla]
		k.player_instance.queue_free()
	players.clear()
	if camera != null:
		camera.queue_free()
	user_id = ""
	user_name = ""
	print("Connection Killed")
	get_node("/root").get_tree().change_scene_to_file("res://Scenes/DirectConnect.tscn")
	print("Scene Changed")

func _exit_tree():
	kill_connection()
	
# Returns whether or not the client is connected	
func connectedToServer() -> bool:
	if OS.get_name() == "Web":
		return WebSocketConnectionHandler.open
	return connected && UDP.is_socket_connected() 

func create_player():
	player = Player.instantiate()
	camera = Camera2D.new()
	camera.zoom = Vector2(0.75, 0.75)
	#camera.process_callback = Camera2D.CAMERA2D_PROCESS_PHYSICS
	var foreign = RemoteTransform2D.new()
	player.add_child(foreign)
	get_node("/root").add_child(camera)
	get_node("/root").add_child(player)
	foreign.remote_path = camera.get_path()
	player.position = ConnectionHandler.players.get(ConnectionHandler.user_id).get_pos()
	ConnectionHandler.players.get(ConnectionHandler.user_id).player_instance.hide()
	
# Changes the dialog information and has it popup in front of the user
func show_popup(title, message):
	if dialog == null:
		return
	dialog.title = title
	dialog.dialog_text = message
	dialog.popup_centered()
