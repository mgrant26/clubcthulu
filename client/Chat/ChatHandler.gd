extends Node

@onready var ConnectionHandler : ConnectionHandler = get_node("/root/ConnectionHandler")
@export_category("Chat Box")
@export var MessageBox : TextEdit

func _ready():
	MessageBox.text = str("Connected To: ", ConnectionHandler.hostname)
	ConnectionHandler.ChatHandler = self

func _process(_delta):
	var queue = ConnectionHandler.chat_queue
	while queue.size() > 0:
		var message = queue.pop_front()
		var user = ConnectionHandler.players.get(message[0])
		MessageBox.text += str("\n", user.player_name, ": ", message[1])
		MessageBox.scroll_vertical += 1000

func player_joined(player):
	MessageBox.text += str("\n", player.player_name, ": joined")
	MessageBox.scroll_vertical += 1000

func player_left(player):
	MessageBox.text += str("\n", player.player_name, " left")
	MessageBox.scroll_vertical += 1000

func _on_chat_bar_focus_entered():
	ConnectionHandler.accept_player_input = false

func _on_chat_bar_focus_exited():
	ConnectionHandler.accept_player_input = true
