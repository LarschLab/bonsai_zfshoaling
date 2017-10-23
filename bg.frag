#version 400

uniform float colBG = 1.0;
out vec4 frag_colour;

void main()
{
   frag_colour = vec4(colBG,colBG,colBG,1);
  //frag_colour = vec4(colBG,0,0,1);
}
