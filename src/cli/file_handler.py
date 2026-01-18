"""File handling utilities for CLI."""

import base64
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console

console = Console()

# File size limit: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


class FileHandler:
    """Handle file attachments for agent invocation."""

    @staticmethod
    def read_file(file_path: Path) -> Dict[str, Any]:
        """
        Read file and prepare for agent consumption.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file content and metadata

        Raises:
            ValueError: If file is too large or unreadable
        """
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")

        # Check file size
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File too large: {file_size / 1024 / 1024:.2f}MB "
                f"(max: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
            )

        suffix = file_path.suffix.lower()

        try:
            # Handle different file types
            if suffix in {".txt", ".md", ".py", ".js", ".json", ".yaml", ".yml", ".csv"}:
                # Text files - read as text
                content = file_path.read_text(encoding="utf-8")
                return {
                    "type": "text",
                    "content": content,
                    "filename": file_path.name,
                    "mime_type": FileHandler._get_mime_type(suffix),
                }

            elif suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
                # Images - base64 encode
                content = file_path.read_bytes()
                encoded = base64.b64encode(content).decode("utf-8")
                return {
                    "type": "image",
                    "content": encoded,
                    "filename": file_path.name,
                    "mime_type": FileHandler._get_mime_type(suffix),
                }

            elif suffix == ".pdf":
                # PDFs - read as bytes for now
                content = file_path.read_bytes()
                encoded = base64.b64encode(content).decode("utf-8")
                return {
                    "type": "pdf",
                    "content": encoded,
                    "filename": file_path.name,
                    "mime_type": "application/pdf",
                }

            else:
                # Unknown type - try text first, then binary
                try:
                    content = file_path.read_text(encoding="utf-8")
                    return {
                        "type": "text",
                        "content": content,
                        "filename": file_path.name,
                        "mime_type": "text/plain",
                    }
                except UnicodeDecodeError:
                    # Binary file
                    content = file_path.read_bytes()
                    encoded = base64.b64encode(content).decode("utf-8")
                    return {
                        "type": "binary",
                        "content": encoded,
                        "filename": file_path.name,
                        "mime_type": "application/octet-stream",
                    }

        except Exception as e:
            raise ValueError(f"Error reading file {file_path}: {e}")

    @staticmethod
    def _get_mime_type(suffix: str) -> str:
        """Get MIME type from file suffix."""
        mime_types = {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".json": "application/json",
            ".yaml": "text/yaml",
            ".yml": "text/yaml",
            ".csv": "text/csv",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".pdf": "application/pdf",
        }
        return mime_types.get(suffix, "application/octet-stream")

    @staticmethod
    def format_file_info(file_data: Dict[str, Any]) -> str:
        """Format file information for display."""
        file_type = file_data["type"]
        filename = file_data["filename"]
        mime = file_data.get("mime_type", "unknown")

        if file_type == "text":
            content_len = len(file_data["content"])
            return f"📄 {filename} ({mime}, {content_len} chars)"
        elif file_type == "image":
            encoded_len = len(file_data["content"])
            return f"🖼️  {filename} ({mime}, {encoded_len} bytes base64)"
        elif file_type == "pdf":
            encoded_len = len(file_data["content"])
            return f"📕 {filename} ({mime}, {encoded_len} bytes base64)"
        else:
            return f"📎 {filename} ({mime})"
