extends Button

@onready var ConnectionHandler = get_node("/root/ConnectionHandler")
@export var ip: LineEdit
@export var port: LineEdit

## Called when the button is pressed
func _pressed():
	# Attempts to connect to the provided IP and Port
	var connected = ConnectionHandler.connect_udp(ip.text, int(port.text))
	# Sends an error if connect_udp returns anything other than OK
	if connected != OK:
		ConnectionHandler.show_popup("Error", "An error occurred")

## Constantly called 
func _process(_delta):
	if ConnectionHandler == null:
		return
	# Checks if the Client is connected to the server
	if ConnectionHandler.connectedToServer():
		# Changes the scene to the LoginScreen if it is connected
		get_tree().change_scene_to_file("res://Scenes/LoginScreen.tscn")
