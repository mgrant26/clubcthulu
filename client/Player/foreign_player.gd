extends Node

@onready var ConnectionHandler = get_node("/root/ConnectionHandler")
var player_factory = preload("res://Player/foreign_player.tscn")
var player_name = "Placeholder"
var player_id = ""
var player_instance: Node
var velocity = Vector2.ZERO
var last_time = 0

func create(scene, n_name, id):
	player_name = n_name
	player_id = id
	player_instance = player_factory.instantiate()
	player_instance.position = Vector2(0, 0)
	var label = Label.new()
	label.text = player_name
	label.position = Vector2(0, 50)
	player_instance.add_child(label)
	self.add_child.call_deferred(player_instance)
	scene.add_child.call_deferred(self)

func _process(_delta):
	if player_instance != null:
		player_instance.position += velocity
	velocity = Vector2.ZERO

func get_pos():
	return player_instance.position

func move(vel):
	velocity += vel

func teleport(loc):
	player_instance.position = loc

func leave(current_scene):
	current_scene.remove_child(self)
	for child in player_instance.get_children():
		child.queue_free()
	player_instance.queue_free()
	queue_free()

