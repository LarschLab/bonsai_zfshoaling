#version 400
uniform vec2 scale = vec2(1, 1);
uniform vec2 shift = vec2(0, 0);
in vec2 vp;
in vec2 vt;
out vec2 tex_coord;
void main()
{
  gl_Position = vec4(vp * scale + shift, 1, 1);
  tex_coord = vt;
}
