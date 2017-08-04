#version 400
out vec4 fragColor;
uniform float colBG = 0.0;
uniform float colDot = 1.0;

void main()
{
  // position of the fragment inside the unit circle
  vec2 position = 2 * gl_PointCoord - 1;

  // fragment is inside the circle when the length is smaller than one
  //vec4 a = color;
  //fragColor = length(position) < 1 ?  vec4(colDot,colDot,colDot,1): vec4(colBG,0,0,1);
  fragColor = length(position) < 1 ?  vec4(colDot,colDot,colDot,1): vec4(colBG,colBG,colBG,1);
  //fragColor = color; //* scale;
}
