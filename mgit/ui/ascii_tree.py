"""
3D ASCII Tree Renderer using donut.c-style mathematics.

Renders a conifer tree (cone foliage + cylinder trunk) with:
- Rotation matrices for spinning animation
- Surface normals for directional lighting
- Character-density mapping for shading
- Z-buffer for proper occlusion
- ANSI color support (green foliage, brown trunk)
"""

import math

# Character luminance gradient (dark to bright)
LUMINANCE_CHARS = " .,-~:;=!*#$@"

# ANSI color codes
COLOR_GREEN = "\033[92m"  # Bright green for foliage
COLOR_BROWN = "\033[38;5;130m"  # Brown for trunk
COLOR_RESET = "\033[0m"

# Tree dimensions (in world units, centered at y=0)
FOLIAGE_HEIGHT = 2.5  # Cone height
FOLIAGE_RADIUS = 1.5  # Base radius of cone
TRUNK_HEIGHT = 0.5  # Cylinder height
TRUNK_RADIUS = 0.25  # Cylinder radius
TREE_CENTER_Y = (FOLIAGE_HEIGHT + TRUNK_HEIGHT) / 2  # Vertical center offset

# Render settings
SCREEN_WIDTH = 60
SCREEN_HEIGHT = 24
K1 = 30  # Projection scaling factor
K2 = 6  # Distance from viewer to center

# Light direction (from upper-right, normalized)
_light_len = math.sqrt(0.4**2 + 0.8**2 + 0.4**2)
LIGHT_X = 0.4 / _light_len
LIGHT_Y = 0.8 / _light_len
LIGHT_Z = -0.4 / _light_len


def _rotate_point(
    x: float, y: float, z: float, sin_a: float, cos_a: float, sin_b: float, cos_b: float
) -> tuple[float, float, float]:
    """Apply rotation matrices for angles A (around X) and B (around Y)."""
    # Rotate around Y axis (angle B)
    x1 = x * cos_b + z * sin_b
    z1 = -x * sin_b + z * cos_b

    # Rotate around X axis (angle A)
    y1 = y * cos_a - z1 * sin_a
    z2 = y * sin_a + z1 * cos_a

    return x1, y1, z2


def _sample_cone_surface(
    theta: float, h: float
) -> tuple[float, float, float, float, float, float]:
    """
    Sample a point on the cone surface (foliage).

    theta: angle around the cone (0 to 2*pi)
    h: height along the cone (0 at base, 1 at tip)

    Returns: (x, y, z, nx, ny, nz) - position and surface normal
    """
    # Radius decreases linearly from base to tip
    radius = FOLIAGE_RADIUS * (1 - h)

    # Position on cone surface (centered at origin)
    x = radius * math.cos(theta)
    z = radius * math.sin(theta)
    y = h * FOLIAGE_HEIGHT + TRUNK_HEIGHT - TREE_CENTER_Y  # Center vertically

    # Surface normal for cone: points outward and upward
    # Normal direction: (cos(theta), slope, sin(theta)) normalized
    slope = FOLIAGE_RADIUS / FOLIAGE_HEIGHT
    normal_len = math.sqrt(1 + slope * slope)
    nx = math.cos(theta) / normal_len
    ny = slope / normal_len
    nz = math.sin(theta) / normal_len

    return x, y, z, nx, ny, nz


def _sample_trunk_surface(
    theta: float, h: float
) -> tuple[float, float, float, float, float, float]:
    """
    Sample a point on the trunk cylinder.

    theta: angle around the cylinder (0 to 2*pi)
    h: height along trunk (0 to 1)

    Returns: (x, y, z, nx, ny, nz) - position and surface normal
    """
    x = TRUNK_RADIUS * math.cos(theta)
    z = TRUNK_RADIUS * math.sin(theta)
    y = h * TRUNK_HEIGHT - TREE_CENTER_Y  # Center vertically

    # Normal for cylinder: points straight outward horizontally
    nx = math.cos(theta)
    ny = 0.0
    nz = math.sin(theta)

    return x, y, z, nx, ny, nz


def render_tree_frame(angle: float, tilt: float = 0.2, use_color: bool = True) -> str:
    """
    Render a single frame of the spinning tree.

    angle: rotation angle around Y axis (spin)
    tilt: constant tilt for 3D perspective
    use_color: whether to include ANSI color codes

    Returns: Multi-line string of ASCII art
    """
    # Initialize screen buffer, z-buffer, and color buffer
    output: list[list[str]] = [
        [" " for _ in range(SCREEN_WIDTH)] for _ in range(SCREEN_HEIGHT)
    ]
    zbuffer: list[list[float]] = [
        [0.0 for _ in range(SCREEN_WIDTH)] for _ in range(SCREEN_HEIGHT)
    ]
    colors: list[list[str]] = [
        ["" for _ in range(SCREEN_WIDTH)] for _ in range(SCREEN_HEIGHT)
    ]

    # Precompute trig values - tilt around X, spin around Y
    sin_a, cos_a = math.sin(tilt), math.cos(tilt)
    sin_b, cos_b = math.sin(angle), math.cos(angle)

    # Rotating light direction for shimmer effect - light orbits with the tree
    light_x = LIGHT_X * cos_b - LIGHT_Z * sin_b
    light_y = LIGHT_Y
    light_z = LIGHT_X * sin_b + LIGHT_Z * cos_b

    # Sample the cone (foliage) - finer steps for denser coverage
    theta_step = 0.03
    h_step = 0.012

    theta = 0.0
    while theta < 2 * math.pi:
        h = 0.0
        while h < 1.0:
            x, y, z, nx, ny, nz = _sample_cone_surface(theta, h)

            # Apply rotation
            rx, ry, rz = _rotate_point(x, y, z, sin_a, cos_a, sin_b, cos_b)
            rnx, rny, rnz = _rotate_point(nx, ny, nz, sin_a, cos_a, sin_b, cos_b)

            # Perspective projection
            ooz = 1 / (rz + K2)
            xp = int(SCREEN_WIDTH / 2 + K1 * ooz * rx)
            yp = int(SCREEN_HEIGHT / 2 - K1 * ooz * ry)  # Invert Y for screen coords

            # Calculate luminance (dot product with rotating light direction)
            luminance = rnx * light_x + rny * light_y + rnz * light_z

            if (
                0 <= xp < SCREEN_WIDTH
                and 0 <= yp < SCREEN_HEIGHT
                and ooz > zbuffer[yp][xp]
            ):
                zbuffer[yp][xp] = ooz
                # Map luminance (-1 to 1) to character index
                lum_idx = int((luminance + 1) * 0.5 * (len(LUMINANCE_CHARS) - 1))
                lum_idx = max(0, min(len(LUMINANCE_CHARS) - 1, lum_idx))
                output[yp][xp] = LUMINANCE_CHARS[lum_idx]
                colors[yp][xp] = COLOR_GREEN  # Foliage is green

            h += h_step
        theta += theta_step

    # Sample the trunk (cylinder)
    theta = 0.0
    while theta < 2 * math.pi:
        h = 0.0
        while h < 1.0:
            x, y, z, nx, ny, nz = _sample_trunk_surface(theta, h)

            # Apply rotation
            rx, ry, rz = _rotate_point(x, y, z, sin_a, cos_a, sin_b, cos_b)
            rnx, rny, rnz = _rotate_point(nx, ny, nz, sin_a, cos_a, sin_b, cos_b)

            # Perspective projection
            ooz = 1 / (rz + K2)
            xp = int(SCREEN_WIDTH / 2 + K1 * ooz * rx)
            yp = int(SCREEN_HEIGHT / 2 - K1 * ooz * ry)

            # Calculate luminance
            luminance = rnx * light_x + rny * light_y + rnz * light_z

            if (
                0 <= xp < SCREEN_WIDTH
                and 0 <= yp < SCREEN_HEIGHT
                and ooz > zbuffer[yp][xp]
            ):
                zbuffer[yp][xp] = ooz
                lum_idx = int((luminance + 1) * 0.5 * (len(LUMINANCE_CHARS) - 1))
                lum_idx = max(0, min(len(LUMINANCE_CHARS) - 1, lum_idx))
                output[yp][xp] = LUMINANCE_CHARS[lum_idx]
                colors[yp][xp] = COLOR_BROWN  # Trunk is brown

            h += h_step
        theta += theta_step

    # Convert buffer to string with optional colors
    if use_color:
        lines = []
        for y in range(SCREEN_HEIGHT):
            line_parts = []
            current_color = ""
            for x in range(SCREEN_WIDTH):
                char = output[y][x]
                color = colors[y][x]
                if char != " " and color and color != current_color:
                    line_parts.append(color)
                    current_color = color
                elif char == " " and current_color:
                    line_parts.append(COLOR_RESET)
                    current_color = ""
                line_parts.append(char)
            if current_color:
                line_parts.append(COLOR_RESET)
            lines.append("".join(line_parts))
        return "\n".join(lines)
    else:
        return "\n".join("".join(row) for row in output)


def get_static_tree(use_color: bool = True) -> str:
    """Return a static ASCII art tree for non-animated contexts."""
    if use_color:
        g = COLOR_GREEN  # Green for foliage
        b = COLOR_BROWN  # Brown for trunk
        r = COLOR_RESET  # Reset
        y = "\033[93m"  # Yellow for star
        c = "\033[96m"  # Cyan for MGIT text
        return f"""
              {y}*{r}
             {g}/|\\{r}
            {g}/*|O\\{r}
           {g}/*/|\\*\\{r}
          {g}/X/O|*\\X\\{r}
         {g}/*/X/|\\O\\*\\{r}
        {g}/O/*/X|*\\X\\O\\{r}
       {g}/*/O/*/|\\*\\O\\*\\{r}
      {g}/X/*/O/X|O\\*\\X\\O\\{r}
     {g}/O/X/*/O/|\\*\\O\\X\\*\\{r}
    {g}/*/O/X/*/X|O\\X\\*\\O\\X\\{r}
   {g}/X/*/O/X/O/|\\O\\X\\O\\*\\O\\{r}
  {g}~~~~~~~~~~~{b}|||{g}~~~~~~~~~~~{r}
             {b}|||{r}
            {b}/|||\\{r}
           {b}/_____\\{r}

        {c}M   G   I   T{r}
    {c}Multi-Git CLI Tool{r}
"""
    else:
        return r"""
              *
             /|\
            /*|O\
           /*/|\*\
          /X/O|*\X\
         /*/X/|\O\*\
        /O/*/X|*\X\O\
       /*/O/*/|\*\O\*\
      /X/*/O/X|O\*\X\O\
     /O/X/*/O/|\*\O\X\*\
    /*/O/X/*/X|O\X\*\O\X\
   /X/*/O/X/O/|\O\X\O\*\O\
  ~~~~~~~~~~~|||~~~~~~~~~~~
             |||
            /|||\
           /_____\

        M   G   I   T
    Multi-Git CLI Tool
"""


def get_tree_height() -> int:
    """Return the height in lines of the rendered tree frame."""
    return SCREEN_HEIGHT
