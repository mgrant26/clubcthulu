extends Button

@export_file("*.tscn") var scene: String

func _pressed():
	get_tree().change_scene_to_file(scene)
