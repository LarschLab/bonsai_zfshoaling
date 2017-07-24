#version 400

uniform float colBG = 0.0;
out vec4 frag_colour;

void main()
{
  frag_colour = vec4(colBG,colBG,colBG,1);
}
