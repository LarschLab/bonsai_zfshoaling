#version 400

layout(points) in;
layout(triangle_strip, max_vertices = 22) out;

out vec2 tex_coord;


//in vec3 vColor[];
//out vec3 fColor;

const float PI = 3.1415926;
vec4 xAll = vec4(0,1,1,0);
vec4 yAll = vec4(1,1,0,0);
// float xAll[8] = float[](0,.25,.75,1,1,.75,.25,0);
// float yAll[8] = float[](.75,1,1,.75,.25,.0,.0,.25);

void main()
{
    //fColor = vColor[0];

    for (int i = 0; i <= 4; i++) {
        // Angle between each side in radians
        //float ang = gl_in[0].gl_Position[2]+(PI / 4.0 + PI * 2.0 / 4 * i);
		float ang = gl_in[0].gl_PointSize+(PI / 4.0 + PI * 2.0 / 4 * i);

        // Offset from center of point (0.3 to accomodate for aspect ratio)
        vec4 offset = vec4(cos(ang) * 0.3*0.5, -sin(ang) * 0.48*0.5, 0.0, 0.0);
        gl_Position = gl_in[0].gl_Position + offset;
		tex_coord=vec2(xAll[i%4],yAll[i%4]);
        EmitVertex();
    }

    EndPrimitive();
}