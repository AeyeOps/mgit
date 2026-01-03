"""
Data compression utilities for change pipeline storage efficiency.

Provides intelligent compression for changeset data, content embeddings,
and large repository datasets with configurable compression levels.
"""

import gzip
import json
import logging
import lzma
import zlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CompressionMethod(Enum):
    """Supported compression methods."""

    NONE = "none"
    GZIP = "gzip"
    LZMA = "lzma"
    ZLIB = "zlib"


@dataclass
class CompressionResult:
    """Result of compression operation."""

    original_size: int
    compressed_size: int
    compression_ratio: float
    method: CompressionMethod
    compressed_data: bytes
    metadata: dict[str, Any]

    @property
    def space_saved_percent(self) -> float:
        """Calculate percentage of space saved."""
        if self.original_size == 0:
            return 0.0
        return ((self.original_size - self.compressed_size) / self.original_size) * 100


class DataCompressor:
    """
    Intelligent data compressor for change pipeline data.

    Automatically selects optimal compression method based on data
    characteristics and provides transparent compression/decompression.
    """

    # Compression level settings
    COMPRESSION_LEVELS = {
        CompressionMethod.GZIP: {"fast": 1, "balanced": 6, "best": 9},
        CompressionMethod.LZMA: {"fast": 1, "balanced": 6, "best": 9},
        CompressionMethod.ZLIB: {"fast": 1, "balanced": 6, "best": 9},
    }

    # Size thresholds for automatic method selection
    GZIP_THRESHOLD = 1024  # 1KB - use gzip for small files
    LZMA_THRESHOLD = 1024 * 100  # 100KB - use lzma for larger files

    def __init__(
        self,
        default_method: CompressionMethod = CompressionMethod.GZIP,
        quality: str = "balanced",
    ):
        """
        Initialize data compressor.

        Args:
            default_method: Default compression method to use
            quality: Compression quality ('fast', 'balanced', 'best')
        """
        self.default_method = default_method
        self.quality = quality

        if quality not in ["fast", "balanced", "best"]:
            raise ValueError(
                f"Invalid quality: {quality}. Must be 'fast', 'balanced', or 'best'"
            )

        logger.debug(
            f"Data compressor initialized: method={default_method.value}, quality={quality}"
        )

    def compress_data(
        self, data: str | bytes, method: CompressionMethod | None = None
    ) -> CompressionResult:
        """
        Compress data using specified or automatic method selection.

        Args:
            data: Data to compress (string or bytes)
            method: Optional compression method override

        Returns:
            CompressionResult with compression details and compressed data
        """
        try:
            # Convert string to bytes if needed
            data_bytes = data.encode("utf-8") if isinstance(data, str) else data

            original_size = len(data_bytes)

            # Select compression method
            if method is None:
                method = self._select_compression_method(original_size)

            # Skip compression for very small data
            if original_size < 100:
                return CompressionResult(
                    original_size=original_size,
                    compressed_size=original_size,
                    compression_ratio=1.0,
                    method=CompressionMethod.NONE,
                    compressed_data=data_bytes,
                    metadata={"reason": "data_too_small"},
                )

            # Perform compression
            if method == CompressionMethod.NONE:
                compressed_data = data_bytes
            elif method == CompressionMethod.GZIP:
                compressed_data = self._compress_gzip(data_bytes)
            elif method == CompressionMethod.LZMA:
                compressed_data = self._compress_lzma(data_bytes)
            elif method == CompressionMethod.ZLIB:
                compressed_data = self._compress_zlib(data_bytes)
            else:
                raise ValueError(f"Unsupported compression method: {method}")

            compressed_size = len(compressed_data)
            compression_ratio = (
                compressed_size / original_size if original_size > 0 else 1.0
            )

            # Add compression metadata
            result = CompressionResult(
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                method=method,
                compressed_data=compressed_data,
                metadata={
                    "quality": self.quality,
                    "original_type": "string" if isinstance(data, str) else "bytes",
                },
            )

            logger.debug(
                f"Compression: {original_size} -> {compressed_size} bytes "
                f"({result.space_saved_percent:.1f}% saved) using {method.value}"
            )

            return result

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            # Return uncompressed data on failure
            return CompressionResult(
                original_size=len(data_bytes) if isinstance(data, str) else len(data),
                compressed_size=len(data_bytes) if isinstance(data, str) else len(data),
                compression_ratio=1.0,
                method=CompressionMethod.NONE,
                compressed_data=data_bytes if isinstance(data, str) else data,
                metadata={"error": str(e)},
            )

    def decompress_data(self, compressed_result: CompressionResult) -> str | bytes:
        """
        Decompress data from CompressionResult.

        Args:
            compressed_result: CompressionResult with compressed data and metadata

        Returns:
            Decompressed data in original format (string or bytes)
        """
        try:
            method = compressed_result.method
            compressed_data = compressed_result.compressed_data

            # Decompress based on method
            if method == CompressionMethod.NONE:
                decompressed_data = compressed_data
            elif method == CompressionMethod.GZIP:
                decompressed_data = gzip.decompress(compressed_data)
            elif method == CompressionMethod.LZMA:
                decompressed_data = lzma.decompress(compressed_data)
            elif method == CompressionMethod.ZLIB:
                decompressed_data = zlib.decompress(compressed_data)
            else:
                raise ValueError(f"Unsupported decompression method: {method}")

            # Convert back to original type if it was string
            original_type = compressed_result.metadata.get("original_type", "bytes")
            if original_type == "string":
                return decompressed_data.decode("utf-8")
            else:
                return decompressed_data

        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise

    def compress_json_data(
        self, data: dict[Any, Any], method: CompressionMethod | None = None
    ) -> CompressionResult:
        """
        Compress JSON-serializable data.

        Args:
            data: Dictionary or other JSON-serializable data
            method: Optional compression method override

        Returns:
            CompressionResult with compressed JSON data
        """
        try:
            # Serialize to compact JSON
            json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

            # Compress the JSON string
            result = self.compress_data(json_str, method)
            result.metadata["data_type"] = "json"

            return result

        except Exception as e:
            logger.error(f"JSON compression failed: {e}")
            raise

    def decompress_json_data(
        self, compressed_result: CompressionResult
    ) -> dict[Any, Any]:
        """
        Decompress JSON data.

        Args:
            compressed_result: CompressionResult containing compressed JSON

        Returns:
            Deserialized JSON data
        """
        try:
            if compressed_result.metadata.get("data_type") != "json":
                logger.warning("CompressionResult not marked as JSON data")

            # Decompress to string
            json_str = self.decompress_data(compressed_result)

            # Deserialize JSON
            return json.loads(json_str)

        except Exception as e:
            logger.error(f"JSON decompression failed: {e}")
            raise

    def _select_compression_method(self, data_size: int) -> CompressionMethod:
        """Select optimal compression method based on data size."""
        if data_size < self.GZIP_THRESHOLD:
            return CompressionMethod.GZIP
        elif data_size < self.LZMA_THRESHOLD:
            return (
                CompressionMethod.GZIP
                if self.quality == "fast"
                else CompressionMethod.LZMA
            )
        else:
            return CompressionMethod.LZMA

    def _compress_gzip(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        level = self.COMPRESSION_LEVELS[CompressionMethod.GZIP][self.quality]
        return gzip.compress(data, compresslevel=level)

    def _compress_lzma(self, data: bytes) -> bytes:
        """Compress data using lzma."""
        preset = self.COMPRESSION_LEVELS[CompressionMethod.LZMA][self.quality]
        return lzma.compress(data, preset=preset)

    def _compress_zlib(self, data: bytes) -> bytes:
        """Compress data using zlib."""
        level = self.COMPRESSION_LEVELS[CompressionMethod.ZLIB][self.quality]
        return zlib.compress(data, level=level)


class FileCompressor:
    """File-based compression utilities for large datasets."""

    def __init__(self, compressor: DataCompressor | None = None):
        """Initialize file compressor."""
        self.compressor = compressor or DataCompressor()

    def compress_file(
        self,
        input_path: Path,
        output_path: Path | None = None,
        method: CompressionMethod | None = None,
    ) -> tuple[Path, CompressionResult]:
        """
        Compress a file and save compressed version.

        Args:
            input_path: Path to input file
            output_path: Optional output path (defaults to input_path + .compressed)
            method: Optional compression method override

        Returns:
            Tuple of (output_path, compression_result)
        """
        try:
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")

            # Read input file
            with input_path.open("rb") as f:
                file_data = f.read()

            # Compress data
            result = self.compressor.compress_data(file_data, method)

            # Determine output path
            if output_path is None:
                suffix_map = {
                    CompressionMethod.GZIP: ".gz",
                    CompressionMethod.LZMA: ".xz",
                    CompressionMethod.ZLIB: ".zlib",
                }
                suffix = suffix_map.get(result.method, ".compressed")
                output_path = input_path.with_suffix(input_path.suffix + suffix)

            # Write compressed file
            with output_path.open("wb") as f:
                f.write(result.compressed_data)

            # Write metadata file
            metadata_path = output_path.with_suffix(output_path.suffix + ".meta")
            metadata = {
                "original_file": str(input_path),
                "compression_method": result.method.value,
                "original_size": result.original_size,
                "compressed_size": result.compressed_size,
                "compression_ratio": result.compression_ratio,
                "metadata": result.metadata,
            }

            with metadata_path.open("w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(
                f"File compressed: {input_path} -> {output_path} "
                f"({result.space_saved_percent:.1f}% space saved)"
            )

            return output_path, result

        except Exception as e:
            logger.error(f"File compression failed: {e}")
            raise

    def decompress_file(
        self, compressed_path: Path, output_path: Path | None = None
    ) -> Path:
        """
        Decompress a compressed file.

        Args:
            compressed_path: Path to compressed file
            output_path: Optional output path for decompressed file

        Returns:
            Path to decompressed file
        """
        try:
            # Read metadata
            metadata_path = compressed_path.with_suffix(
                compressed_path.suffix + ".meta"
            )
            if not metadata_path.exists():
                raise FileNotFoundError(
                    f"Compression metadata not found: {metadata_path}"
                )

            with metadata_path.open("r") as f:
                metadata = json.load(f)

            # Read compressed data
            with compressed_path.open("rb") as f:
                compressed_data = f.read()

            # Create compression result for decompression
            result = CompressionResult(
                original_size=metadata["original_size"],
                compressed_size=metadata["compressed_size"],
                compression_ratio=metadata["compression_ratio"],
                method=CompressionMethod(metadata["compression_method"]),
                compressed_data=compressed_data,
                metadata=metadata["metadata"],
            )

            # Decompress data
            decompressed_data = self.compressor.decompress_data(result)

            # Determine output path
            if output_path is None:
                original_path = Path(metadata["original_file"])
                output_path = compressed_path.parent / original_path.name

            # Write decompressed file
            with output_path.open("wb") as f:
                if isinstance(decompressed_data, str):
                    f.write(decompressed_data.encode("utf-8"))
                else:
                    f.write(decompressed_data)

            logger.info(f"File decompressed: {compressed_path} -> {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"File decompression failed: {e}")
            raise
