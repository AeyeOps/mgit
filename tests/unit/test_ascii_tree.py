"""Unit tests for ASCII tree renderer."""

import math

from mgit.ui.ascii_tree import (
    LUMINANCE_CHARS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    _rotate_point,
    _sample_cone_surface,
    _sample_trunk_surface,
    get_static_tree,
    get_tree_height,
    render_tree_frame,
)


class TestRotatePoint:
    """Tests for 3D rotation matrix."""

    def test_identity_rotation(self):
        """Zero rotation angles produce identity transformation."""
        x, y, z = 1.0, 2.0, 3.0
        sin_a, cos_a = math.sin(0), math.cos(0)  # 0 = no rotation
        sin_b, cos_b = math.sin(0), math.cos(0)

        rx, ry, rz = _rotate_point(x, y, z, sin_a, cos_a, sin_b, cos_b)

        assert abs(rx - x) < 1e-10
        assert abs(ry - y) < 1e-10
        assert abs(rz - z) < 1e-10

    def test_90_degree_y_rotation(self):
        """90 degree rotation around Y axis swaps X and Z."""
        x, y, z = 1.0, 0.0, 0.0
        angle_b = math.pi / 2  # 90 degrees
        sin_a, cos_a = 0.0, 1.0  # No X rotation
        sin_b, cos_b = math.sin(angle_b), math.cos(angle_b)

        rx, ry, rz = _rotate_point(x, y, z, sin_a, cos_a, sin_b, cos_b)

        # Point on +X axis should rotate to +Z axis
        assert abs(rx) < 1e-10
        assert abs(ry) < 1e-10
        assert abs(rz - (-1.0)) < 1e-10  # Note: rotation direction

    def test_rotation_preserves_distance(self):
        """Rotation should preserve distance from origin."""
        x, y, z = 1.0, 2.0, 3.0
        original_dist = math.sqrt(x**2 + y**2 + z**2)

        # Random rotation angles
        sin_a, cos_a = math.sin(0.7), math.cos(0.7)
        sin_b, cos_b = math.sin(1.2), math.cos(1.2)

        rx, ry, rz = _rotate_point(x, y, z, sin_a, cos_a, sin_b, cos_b)
        rotated_dist = math.sqrt(rx**2 + ry**2 + rz**2)

        assert abs(rotated_dist - original_dist) < 1e-10


class TestSampleSurfaces:
    """Tests for surface sampling functions."""

    def test_cone_surface_returns_6_values(self):
        """Cone surface sampling returns position and normal."""
        result = _sample_cone_surface(0.0, 0.5)
        assert len(result) == 6

    def test_trunk_surface_returns_6_values(self):
        """Trunk surface sampling returns position and normal."""
        result = _sample_trunk_surface(0.0, 0.5)
        assert len(result) == 6

    def test_cone_normal_is_unit_vector(self):
        """Cone surface normal should be approximately unit length."""
        x, y, z, nx, ny, nz = _sample_cone_surface(1.0, 0.3)
        normal_len = math.sqrt(nx**2 + ny**2 + nz**2)
        assert abs(normal_len - 1.0) < 1e-10

    def test_trunk_normal_is_unit_vector(self):
        """Trunk surface normal should be unit length."""
        x, y, z, nx, ny, nz = _sample_trunk_surface(1.0, 0.5)
        normal_len = math.sqrt(nx**2 + ny**2 + nz**2)
        assert abs(normal_len - 1.0) < 1e-10

    def test_cone_tip_has_small_radius(self):
        """At h=1.0 (tip), cone radius should be near zero."""
        x, y, z, nx, ny, nz = _sample_cone_surface(0.0, 0.99)
        radius = math.sqrt(x**2 + z**2)
        assert radius < 0.1  # Should be very small near tip


class TestRenderTreeFrame:
    """Tests for the frame rendering function."""

    def test_frame_has_correct_dimensions(self):
        """Rendered frame should have expected line count."""
        frame = render_tree_frame(0.0, use_color=False)
        lines = frame.split("\n")
        assert len(lines) == SCREEN_HEIGHT

    def test_frame_lines_have_correct_width(self):
        """Each line should have expected character count."""
        frame = render_tree_frame(0.0, use_color=False)
        for line in frame.split("\n"):
            assert len(line) == SCREEN_WIDTH

    def test_frame_contains_only_valid_chars(self):
        """Frame should only contain luminance characters and spaces."""
        frame = render_tree_frame(0.0, use_color=False)
        valid_chars = set(LUMINANCE_CHARS)
        for char in frame:
            if char != "\n":
                assert char in valid_chars, f"Invalid char: {repr(char)}"

    def test_different_angles_produce_different_frames(self):
        """Different rotation angles should produce different output."""
        frame1 = render_tree_frame(0.0, use_color=False)
        frame2 = render_tree_frame(math.pi / 2, use_color=False)

        # Frames should be different (lighting changes with rotation)
        assert frame1 != frame2

    def test_frame_is_not_empty(self):
        """Frame should contain some non-space characters (the tree)."""
        frame = render_tree_frame(0.0, use_color=False)
        non_space_chars = [c for c in frame if c not in " \n"]
        assert len(non_space_chars) > 50  # Should have substantial content

    def test_frame_with_color_contains_ansi_codes(self):
        """Colored frame should contain ANSI escape codes."""
        frame = render_tree_frame(0.0, use_color=True)
        assert "\033[" in frame  # ANSI escape sequence


class TestStaticTree:
    """Tests for static tree art."""

    def test_static_tree_is_string(self):
        """Static tree should return a string."""
        tree = get_static_tree()
        assert isinstance(tree, str)

    def test_static_tree_has_content(self):
        """Static tree should have multiple lines."""
        tree = get_static_tree()
        lines = [line for line in tree.split("\n") if line.strip()]
        assert len(lines) > 5

    def test_static_tree_contains_mgit(self):
        """Static tree should contain MGIT branding."""
        tree = get_static_tree()
        assert "M" in tree and "G" in tree and "I" in tree and "T" in tree


class TestGetTreeHeight:
    """Tests for tree height helper."""

    def test_tree_height_matches_screen_height(self):
        """Tree height should match screen dimensions."""
        assert get_tree_height() == SCREEN_HEIGHT

    def test_tree_height_is_reasonable(self):
        """Tree height should be reasonable for terminal display."""
        height = get_tree_height()
        assert 10 <= height <= 50  # Reasonable terminal range
