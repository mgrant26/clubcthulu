//https://godotshaders.com/shader/2d-outline-stroke/
//https://godotshaders.com/shader/outline-that-disrespects-boundaries/
//Just a bit more compressed
shader_type canvas_item;

uniform vec4 line_color : source_color = vec4(1);
uniform float line_thickness : hint_range(0.0, 20) = 0.0;
uniform bool add_margins = true;

void vertex() {
	if (add_margins) {
		VERTEX += ((UV * 2.0) - 1.0) * line_thickness;
	}
}

void fragment() {
	vec2 uv = UV;
	vec2 t_size = vec2(1.0) / ((vec2(1.0) / TEXTURE_PIXEL_SIZE) + vec2(line_thickness*2.));
	
	uv = (uv - (t_size * line_thickness)) * TEXTURE_PIXEL_SIZE / t_size;
	
	if (uv != clamp(uv, vec2(0.0), vec2(1.0))) {
		COLOR.a = 0.0;
	} else {
		COLOR = texture(TEXTURE, uv);
	}
	
	vec2 size = TEXTURE_PIXEL_SIZE * line_thickness;
	
	if (line_thickness < 0.1) {
		vec4 color = texture(TEXTURE, uv);
		
	} else {
		float outline = 0.;
		for (float y = -3.; y <= 3.; y+= .3) {
			for (float x = -3.; x <= 3.; x+= .3) {
				if (x==0. && y == 0.)
					continue;
				outline += texture(TEXTURE, uv + vec2(x*size.x, y*size.y)).a;
			}
		}
		outline = min(outline, 1.);
		vec4 color = texture(TEXTURE, uv);
		COLOR = mix(color, line_color, outline - color.a);
	}
}
