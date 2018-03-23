#version 400
uniform vec2 scale = vec2(1, 1);
uniform vec2 shift;// = vec2(0, 0);
in vec3 vp;

void main()
{
  gl_Position = vec4(vp.xy * scale + shift, 0.0, 1.0);
  gl_PointSize = vp.z;
}
