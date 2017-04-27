#version 400

layout(points) in;
layout(triangle_strip, max_vertices = 6) out;
out vec2 tex_coord;

//in vec3 vColor[];
//out vec3 fColor;

const float PI = 3.1415926;
vec4 xAll = vec4(0,1,1,0);
vec4 yAll = vec4(1,1,0,0);

void main()
{
    //fColor = vColor[0];

    for (int i = 0; i <= 4; i++) {
        // Angle between each side in radians
        float ang = PI / 4.0 + PI * 2.0 / 4 * i;

        // Offset from center of point (0.3 to accomodate for aspect ratio)
        vec4 offset = vec4(cos(ang) * 0.3*0.8, -sin(ang) * 0.48*0.8, 0.0, 0.0);
        gl_Position = gl_in[0].gl_Position + offset;
		tex_coord=vec2(xAll[i%4],yAll[i%4]);
        EmitVertex();
    }

    EndPrimitive();
}