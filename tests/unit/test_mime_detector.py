"""
Unit tests for MIME detector and content safety validation.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from mgit.content.mime_detector import MimeDetector, MimeInfo, ContentSafety


class TestMimeDetector:
    @pytest.fixture
    def mime_detector(self):
        return MimeDetector()

    def test_detect_python_file(self, mime_detector):
        """Test MIME detection for Python files."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write('print("hello world")\n')
            temp_path = Path(f.name)

        try:
            mime_info = mime_detector.detect_file_info(temp_path)
            assert mime_info.mime_type == "text/x-python"
            assert mime_info.safety == ContentSafety.SAFE_CODE
            assert mime_info.is_text is True
            assert mime_info.is_binary is False
            assert mime_info.file_extension == ".py"
            assert mime_info.confidence == 0.9

        finally:
            temp_path.unlink()

    def test_detect_json_file(self, mime_detector):
        """Test MIME detection for JSON files."""
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write('{"test": "data"}\n')
            temp_path = Path(f.name)

        try:
            mime_info = mime_detector.detect_file_info(temp_path)
            assert mime_info.mime_type == "application/json"
            assert mime_info.safety == ContentSafety.SAFE_STRUCTURED
            assert mime_info.is_text is True
            assert mime_info.confidence == 0.9

        finally:
            temp_path.unlink()

    def test_detect_binary_extension(self, mime_detector):
        """Test handling of known binary extensions."""
        with tempfile.NamedTemporaryFile(suffix=".exe", mode="wb", delete=False) as f:
            f.write(b"binary content")
            temp_path = Path(f.name)

        try:
            mime_info = mime_detector.detect_file_info(temp_path)
            assert mime_info.safety == ContentSafety.UNSAFE_BINARY
            assert mime_info.is_binary is True
            assert mime_info.is_text is False
            assert mime_info.file_extension == ".exe"

        finally:
            temp_path.unlink()

    def test_detect_large_file(self, mime_detector):
        """Test handling of files exceeding size limits."""
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            # Write content that exceeds MAX_SAFE_SIZE
            large_content = "x" * (mime_detector.MAX_SAFE_SIZE + 100)
            f.write(large_content)
            temp_path = Path(f.name)

        try:
            mime_info = mime_detector.detect_file_info(temp_path)
            assert mime_info.safety == ContentSafety.UNSAFE_LARGE
            assert mime_info.size_bytes > mime_detector.MAX_SAFE_SIZE

        finally:
            temp_path.unlink()

    def test_detect_unknown_extension(self, mime_detector):
        """Test fallback for unknown file extensions."""
        with tempfile.NamedTemporaryFile(
            suffix=".unknownext", mode="w", delete=False
        ) as f:
            f.write("some text content\n")
            temp_path = Path(f.name)

        try:
            mime_info = mime_detector.detect_file_info(temp_path)
            # Should fall back to Python mimetypes or content detection
            assert mime_info.confidence < 0.9  # Lower confidence for fallback
            assert mime_info.file_extension == ".unknownext"

        finally:
            temp_path.unlink()

    def test_nonexistent_file(self, mime_detector):
        """Test handling of non-existent files."""
        fake_path = Path("/nonexistent/file.txt")
        mime_info = mime_detector.detect_file_info(fake_path)

        assert mime_info.safety == ContentSafety.UNSAFE_UNKNOWN
        assert mime_info.size_bytes == 0
        assert mime_info.confidence == 0.0
        assert mime_info.mime_type == "application/octet-stream"

    def test_is_safe_for_embedding(self, mime_detector):
        """Test safety check method."""
        # Test with safe Python file
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write('print("hello")\n')
            safe_path = Path(f.name)

        try:
            assert mime_detector.is_safe_for_embedding(safe_path) is True
        finally:
            safe_path.unlink()

        # Test with unsafe binary file
        with tempfile.NamedTemporaryFile(suffix=".exe", mode="wb", delete=False) as f:
            f.write(b"binary")
            unsafe_path = Path(f.name)

        try:
            assert mime_detector.is_safe_for_embedding(unsafe_path) is False
        finally:
            unsafe_path.unlink()

    @patch("subprocess.run")
    def test_file_command_detection(self, mock_run, mime_detector):
        """Test system 'file' command integration."""
        # Mock successful file command output
        mock_run.return_value = MagicMock(
            returncode=0, stdout="test.txt: text/plain charset=utf-8\n"
        )

        with tempfile.NamedTemporaryFile(
            suffix=".unknownext", mode="w", delete=False
        ) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            # Force file command usage by removing from SAFE_EXTENSIONS
            original_extensions = mime_detector.SAFE_EXTENSIONS.copy()
            mime_detector.SAFE_EXTENSIONS.clear()

            mime_info = mime_detector.detect_file_info(temp_path)

            # Should use file command result
            assert mime_info.mime_type == "text/plain"
            assert mime_info.charset == "utf-8"
            assert mime_info.confidence == 0.8

        finally:
            temp_path.unlink()
            mime_detector.SAFE_EXTENSIONS.update(original_extensions)

    def test_content_based_detection(self, mime_detector):
        """Test content-based MIME detection."""
        # Test shell script detection
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write('#!/bin/bash\necho "hello"\n')
            script_path = Path(f.name)

        try:
            # Clear safe extensions to force content detection
            original_extensions = mime_detector.SAFE_EXTENSIONS.copy()
            mime_detector.SAFE_EXTENSIONS.clear()

            # Simulate file command not available
            mime_detector.has_file_command = False

            mime_info = mime_detector.detect_file_info(script_path)

            # Should detect as shell script based on shebang
            assert mime_info.mime_type == "application/x-sh"
            assert mime_info.confidence == 0.5  # Content-based detection

        finally:
            script_path.unlink()
            mime_detector.SAFE_EXTENSIONS.update(original_extensions)
            mime_detector.has_file_command = mime_detector._check_file_command()

    def test_safety_classification_priority(self, mime_detector):
        """Test that structured data types are classified correctly."""
        test_cases = [
            ("application/json", ContentSafety.SAFE_STRUCTURED),
            ("application/yaml", ContentSafety.SAFE_STRUCTURED),
            ("application/xml", ContentSafety.SAFE_STRUCTURED),
            ("text/x-python", ContentSafety.SAFE_CODE),
            ("text/plain", ContentSafety.SAFE_TEXT),
            ("application/octet-stream", ContentSafety.UNSAFE_UNKNOWN),
        ]

        for mime_type, expected_safety in test_cases:
            safety = mime_detector._classify_content_safety(mime_type, 1024, ".test")
            assert (
                safety == expected_safety
            ), f"Failed for {mime_type}: expected {expected_safety}, got {safety}"

    def test_text_type_detection(self, mime_detector):
        """Test text vs binary type classification."""
        text_types = [
            "text/plain",
            "application/json",
            "text/x-python",
            "application/javascript",
        ]

        binary_types = ["application/octet-stream", "image/jpeg", "application/zip"]

        for mime_type in text_types:
            assert (
                mime_detector._is_text_type(mime_type) is True
            ), f"{mime_type} should be text"

        for mime_type in binary_types:
            assert (
                mime_detector._is_text_type(mime_type) is False
            ), f"{mime_type} should be binary"

    def test_size_limits_constants(self):
        """Test that size limit constants are set correctly."""
        detector = MimeDetector()
        assert detector.MAX_SAFE_SIZE == 1024 * 1024  # 1MB default
        assert detector.MAX_SAMPLE_SIZE == 64 * 1024  # 64KB default

    def test_comprehensive_extension_coverage(self, mime_detector):
        """Test that common file extensions are properly mapped."""
        # Test common code extensions
        code_extensions = [".py", ".js", ".java", ".go", ".rs", ".cpp"]
        for ext in code_extensions:
            assert ext in mime_detector.SAFE_EXTENSIONS

        # Test structured data extensions
        data_extensions = [".json", ".yaml", ".xml", ".toml"]
        for ext in data_extensions:
            assert ext in mime_detector.SAFE_EXTENSIONS

        # Test binary extensions are properly marked unsafe
        binary_extensions = [".exe", ".jpg", ".zip", ".pdf"]
        for ext in binary_extensions:
            assert ext in mime_detector.UNSAFE_BINARY_EXTENSIONS

    def test_binary_content_security(self, mime_detector):
        """Test that binary content is detected regardless of file extension."""
        # Test binary file with text extension - CRITICAL SECURITY TEST
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb", delete=False) as f:
            # Write binary content with null bytes (ELF header signature)
            binary_content = b"\x7fELF\x01\x01\x01\x00" + b"\x00" * 50
            f.write(binary_content)
            fake_txt_path = Path(f.name)

        try:
            mime_info = mime_detector.detect_file_info(fake_txt_path)
            # Must be detected as unsafe binary despite .txt extension
            assert mime_info.safety == ContentSafety.UNSAFE_BINARY
            assert mime_info.is_binary is True
            assert mime_info.confidence >= 0.9
        finally:
            fake_txt_path.unlink()

    def test_configurable_size_limits(self):
        """Test that size limits can be configured via constructor."""
        custom_detector = MimeDetector(max_safe_size=2048, max_sample_size=512)
        assert custom_detector.MAX_SAFE_SIZE == 2048
        assert custom_detector.MAX_SAMPLE_SIZE == 512

    def test_dockerfile_without_extension(self, mime_detector):
        """Test detection of Dockerfile without extension."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            dockerfile_content = b"FROM ubuntu:20.04\nRUN apt-get update\n"
            f.write(dockerfile_content)
            # Rename to remove extension
            dockerfile_path = Path(f.name).parent / "Dockerfile"
            Path(f.name).rename(dockerfile_path)

        try:
            mime_info = mime_detector.detect_file_info(dockerfile_path)
            assert mime_info.mime_type == "text/x-dockerfile"
            assert mime_info.safety == ContentSafety.SAFE_CODE
        finally:
            if dockerfile_path.exists():
                dockerfile_path.unlink()
