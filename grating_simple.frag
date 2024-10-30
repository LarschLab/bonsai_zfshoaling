#version 400
const float pi = 3.1415926535897932384626433832795;
const float sqrtTwoPi = sqrt(2 * pi);
uniform int square = 0;
uniform float radius = 1;
uniform float edge = 0;
uniform float frequency = 1;
uniform float contrast = 1;
uniform float phase = 0;
uniform float opacity = 1;
in vec2 tex_coord;
out vec4 frag_colour;
const float zero = 0.0;
void main()
{
  float value = sin(sqrt(pow(tex_coord.x-.5,2)+pow(tex_coord.y-.5,2)) * 2 * pi * frequency + phase); // concentric rings
  //float value = sin((tex_coord.x + phase/100) * 2 * pi * frequency);  // sinewave
  
  value = value * contrast; // contrast modulation
  //value = zero;
  
  if (contrast == 1)
  
  {
  frag_colour = vec4(1, 1, 1, 0);
  }
  else
  {
  frag_colour = vec4(value, value, value, 1.0);
  }
  

}