#version 400
const float twopi = 2 * 3.141592653589793238462643383279;
uniform float frequency;
uniform float phase;
uniform vec4 color;
in vec2 tex_coord;
out vec4 frag_colour;

void main()
{
   float value = 0.5+(0.5*(0.5f * sin(sqrt(pow(tex_coord.x-.5,2)+pow(tex_coord.y-.5,2)) * twopi * frequency + phase) + 0.5f));
  //float value = (0.5f * sin(tex_coord.x * twopi * frequency + phase) + 0.5f);
  frag_colour = vec4(value,value,value,1);
}
