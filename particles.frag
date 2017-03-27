#version 400
out vec4 fragColor;
//uniform vec4 color;

void main()
{
  // position of the fragment inside the unit circle
  vec2 position = 2 * gl_PointCoord - 1;

  // fragment is inside the circle when the length is smaller than one
  //vec4 a = color;
  fragColor = length(position) < 1 ? vec4(0,0,0,1) : vec4(1,1,1,1);

  //fragColor = color; //* scale;
}
