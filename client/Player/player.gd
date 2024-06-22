extends Area2D
#player custom signal
signal hit

@onready var ConnectionHandler: ConnectionHandler = get_node("/root/ConnectionHandler")
@export var speed = 50 # How fast the player will move (pixels/sec).
var screen_size # Size of the game window.
var label
var last_vel = Vector2.ZERO

# Called when the node enters the scene tree for the first time.
func _ready():
	screen_size = get_viewport_rect().size
	label = Label.new()
	label.position.y = -200
	add_child(label)
	
# Called every frame. 'delta' is the elapsed time since the previous frame.
func _physics_process(_delta):
	
	##layers movement vector
	var velocity = Vector2.ZERO 
	var pressed = false
	
	if ConnectionHandler.accept_player_input == true:
		if Input.is_action_pressed("move_right"):
			velocity.x += 1
			pressed = true
		if Input.is_action_pressed("move_left"):
			velocity.x -= 1
			pressed = true
		if Input.is_action_pressed("move_down"):
			velocity.y += 1
			pressed = true
		if Input.is_action_pressed("move_up"):
			velocity.y -= 1
			pressed = true
	
	if pressed:
		$AnimatedSprite2D.play()
	
	#position += velocity
	if velocity.length() > 0 and velocity != last_vel:
		last_vel = velocity
		velocity = velocity.normalized() * speed 
		ConnectionHandler.queue_move(position, velocity)
		ConnectionHandler.move()
	if ConnectionHandler.moving == true && velocity.length() == 0 :
		ConnectionHandler.end_move()
		last_vel = Vector2.ZERO
		$AnimatedSprite2D.stop()
	
	#clamp to prevent character leave the screen
	label.text = "%d, %d\n%d %d" % [fmod(position.x, ConnectionHandler.chunk_width), fmod(position.y, ConnectionHandler.chunk_height), int(position.x / ConnectionHandler.chunk_width), int(position.y / ConnectionHandler.chunk_height)]
	
	position = ConnectionHandler.players.get(ConnectionHandler.user_id).get_pos()
	
	#attach animation
	if velocity.x != 0:
		$AnimatedSprite2D.animation = "walk"
		$AnimatedSprite2D.flip_v = false
		#$AnimatedSprite2D.flip_h = velocity.x < 0

func _on_body_entered(_body):
	pass
	#proximity chat later

func start(pos):
	position = pos
	show()
	$CollisionShape2D.disabled = false
