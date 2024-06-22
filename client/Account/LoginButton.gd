extends Button

@onready var ConnectionHandler = get_node("/root/ConnectionHandler")
@export var username: LineEdit
@export var password: LineEdit

## Called when the button is pressed
func _pressed():
	var login = ConnectionHandler.login(username.text, password.text)
	print(login)

## Called constantly
func _process(_delta):
	#Does nothing if connection handler doesn't exist for some reason
	if not ConnectionHandler or ConnectionHandler == null:
		return
		
	#Checks if the session id is set
	if (!ConnectionHandler.session_id.is_empty()):
		#Change to the GameScene screen when it is set
		get_tree().change_scene_to_file("res://Scenes/GameScene.tscn")
		
