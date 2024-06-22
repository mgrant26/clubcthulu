extends Button

@export_category("Chat")
@export var chat_bar: LineEdit

@onready var ConnectionHandler = get_node("/root/ConnectionHandler")

## Called when the button is pressed
func _pressed():
	# Pulls the text from chat_bar
	var hold = chat_bar.text

	#Clears the chat_bar
	chat_bar.clear()
	
	# Sends the message to ConnectionHandler
	ConnectionHandler.sendMessage(hold)
	chat_bar.release_focus()
	release_focus()

func _on_chat_bar_text_submitted(_new_text):
	_pressed()
