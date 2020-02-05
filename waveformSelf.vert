#version 400

uniform vec2 scale = vec2(1, 1);

in vec3 vp;

void main()
{

  gl_Position = vec4(vp.xy * scale, 0.0, 1.0);
  gl_PointSize = vp.z;
  
}
