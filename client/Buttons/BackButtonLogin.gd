extends Button
@onready var ConnectionHandler = get_node("/root/ConnectionHandler")

## Called when the button is pressed
func _pressed():
	# Changes the scene back to the DirectConnect Screen
	get_tree().change_scene_to_file("res://Scenes/DirectConnect.tscn")
	# Kills the connection to the server
	ConnectionHandler.kill_connection()
