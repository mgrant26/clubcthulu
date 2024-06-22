extends Button

@onready var ConnectionHandler = get_node("/root/ConnectionHandler")
@export var username: LineEdit
@export var password: LineEdit
@export var verify_password: LineEdit


# Called when the node enters the scene tree for the first time.
func _pressed():
	var register = ConnectionHandler.register(username.text, password.text, verify_password.text)
	print(register)
