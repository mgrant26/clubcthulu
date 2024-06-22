extends LineEdit

var regex = RegEx.new()
var old = ""

## Called when the node enters the scene tree for the first time.
func _ready():
	# The regex asserts that the string is either blank or contains only numeric characters
	regex.compile("^$|^[0-9]*$") #Compiles the regex 

## Called whenever the text within the LineEdit changes
func _on_text_changed(new_text):
	# Checks if the new text matches the regex 
	if regex.search(new_text):
		# Converts text to an integer
		var hold = int(new_text)
		# Clamps the vlaue to 0 -> 65535 which contains all valid port numbers except 0
		if hold >= 0 && hold <= 65535:
			old = str(new_text)
		else:
			reset_text()
	else:
		reset_text()

## Resets the 
func reset_text():
	text = old
	set_caret_column(text.length())


func _on_connect_pressed():
	pass # Replace with function body.
