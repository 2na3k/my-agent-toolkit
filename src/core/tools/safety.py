"""Safety validation for tool execution."""

import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from ..logger import get_logger


@dataclass
class SafetyRule:
    """Represents a safety rule for validation."""

    name: str
    pattern: str
    severity: str  # "error", "warning"
    message: str
    category: str  # e.g., "filesystem", "network", "system"


class SafetyValidator:
    """
    Validates tool parameters and commands for dangerous operations.

    Checks for patterns that could cause data loss, system damage, or
    security vulnerabilities.
    """

    # Dangerous filesystem operations
    DANGEROUS_FS_PATTERNS = [
        SafetyRule(
            name="rm_rf",
            pattern=r"\brm\s+(-[a-z]*r[a-z]*f|--recursive\s+--force|-fr|-rf)\b",
            severity="error",
            message="Recursive force removal detected (rm -rf)",
            category="filesystem",
        ),
        SafetyRule(
            name="rm_root",
            pattern=r"\brm\b.*\s+(-r|--recursive).*(/\s|/\*)",
            severity="error",
            message="Removal of root directory or critical paths",
            category="filesystem",
        ),
        SafetyRule(
            name="mkfs",
            pattern=r"\bmkfs\b",
            severity="error",
            message="Filesystem creation/formatting detected (mkfs)",
            category="filesystem",
        ),
        SafetyRule(
            name="dd_dangerous",
            pattern=r"\bdd\b.*\bof=/dev/(sd[a-z]|hd[a-z]|nvme[0-9])",
            severity="error",
            message="Direct disk write detected (dd to block device)",
            category="filesystem",
        ),
        SafetyRule(
            name="format_disk",
            pattern=r"\b(fdisk|parted|gdisk)\b",
            severity="error",
            message="Disk partitioning/formatting tool detected",
            category="filesystem",
        ),
    ]

    # Dangerous system operations
    DANGEROUS_SYSTEM_PATTERNS = [
        SafetyRule(
            name="shutdown",
            pattern=r"\b(shutdown|poweroff|reboot|init\s+[06])\b",
            severity="error",
            message="System shutdown/reboot command detected",
            category="system",
        ),
        SafetyRule(
            name="kill_all",
            pattern=r"\bkillall\b.*-9",
            severity="warning",
            message="Force kill all processes (killall -9)",
            category="system",
        ),
        SafetyRule(
            name="fork_bomb",
            pattern=r":\(\)\{.*:\|:.*\};:",
            severity="error",
            message="Fork bomb pattern detected",
            category="system",
        ),
        SafetyRule(
            name="chmod_777",
            pattern=r"\bchmod\b.*777",
            severity="warning",
            message="Overly permissive permissions (chmod 777)",
            category="system",
        ),
        SafetyRule(
            name="disable_firewall",
            pattern=r"\b(ufw|iptables|firewalld)\b.*(disable|stop|flush|--flush)",
            severity="warning",
            message="Firewall modification detected",
            category="system",
        ),
    ]

    # Dangerous network operations
    DANGEROUS_NETWORK_PATTERNS = [
        SafetyRule(
            name="curl_pipe_sh",
            pattern=r"\bcurl\b.*\|\s*(bash|sh|zsh)",
            severity="error",
            message="Piping remote content to shell (curl | sh)",
            category="network",
        ),
        SafetyRule(
            name="wget_pipe_sh",
            pattern=r"\bwget\b.*-O\s*-.*\|\s*(bash|sh|zsh)",
            severity="error",
            message="Piping remote content to shell (wget | sh)",
            category="network",
        ),
    ]

    # Dangerous code execution
    DANGEROUS_EXEC_PATTERNS = [
        SafetyRule(
            name="eval",
            pattern=r"\beval\b\s*\(",
            severity="warning",
            message="Use of eval() for code execution",
            category="execution",
        ),
        SafetyRule(
            name="exec",
            pattern=r"\bexec\b\s*\(",
            severity="warning",
            message="Use of exec() for code execution",
            category="execution",
        ),
    ]

    # Path-based checks
    DANGEROUS_PATHS = [
        "/",
        "/etc",
        "/bin",
        "/sbin",
        "/usr",
        "/var",
        "/boot",
        "/sys",
        "/proc",
    ]

    def __init__(self):
        """Initialize the safety validator."""
        self.logger = get_logger("tool.safety")

        # Combine all rules
        self.rules = (
            self.DANGEROUS_FS_PATTERNS
            + self.DANGEROUS_SYSTEM_PATTERNS
            + self.DANGEROUS_NETWORK_PATTERNS
            + self.DANGEROUS_EXEC_PATTERNS
        )

        # Compile regex patterns for performance
        self._compiled_patterns = {
            rule.name: re.compile(rule.pattern, re.IGNORECASE) for rule in self.rules
        }

    def validate_command(
        self, command: str, allow_warnings: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate a shell command for dangerous patterns.

        Args:
            command: Shell command to validate
            allow_warnings: If False, treat warnings as errors

        Returns:
            Tuple of (is_safe, list of violations)
        """
        violations = []
        has_errors = False

        for rule in self.rules:
            pattern = self._compiled_patterns[rule.name]
            if pattern.search(command):
                violation = f"[{rule.severity.upper()}] {rule.message}"
                violations.append(violation)

                if rule.severity == "error":
                    has_errors = True
                elif rule.severity == "warning" and not allow_warnings:
                    has_errors = True

                self.logger.warning(
                    f"Safety violation in command: {rule.name} - {rule.message}"
                )

        is_safe = not has_errors
        return is_safe, violations

    def validate_path(self, path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a filesystem path for dangerous locations.

        Args:
            path: File or directory path to validate

        Returns:
            Tuple of (is_safe, error_message)
        """
        # Normalize path
        normalized = path.rstrip("/")

        # Check against dangerous paths
        for dangerous_path in self.DANGEROUS_PATHS:
            if normalized == dangerous_path:
                message = f"Access to critical system path denied: {path}"
                self.logger.error(message)
                return False, message

            # Check if trying to modify under critical paths
            if normalized.startswith(dangerous_path + "/"):
                # Allow read-only access, but warn about modifications
                message = f"Modification of system path may be dangerous: {path}"
                self.logger.warning(message)
                # Return True but with warning message
                return True, message

        return True, None

    def validate_parameters(
        self, tool_name: str, params: Dict[str, Any], allow_warnings: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate tool parameters for dangerous values.

        Args:
            tool_name: Name of the tool being executed
            params: Tool parameters to validate
            allow_warnings: If False, treat warnings as errors

        Returns:
            Tuple of (is_safe, list of violations)
        """
        violations = []

        # Check string parameters for command injection patterns
        for key, value in params.items():
            if isinstance(value, str):
                # Check for command patterns
                is_safe, cmd_violations = self.validate_command(value, allow_warnings)
                if not is_safe or cmd_violations:
                    violations.extend(
                        [f"Parameter '{key}': {v}" for v in cmd_violations]
                    )

                # Check for path patterns (if key suggests it's a path)
                if any(
                    path_key in key.lower()
                    for path_key in ["path", "file", "dir", "directory"]
                ):
                    is_safe, error = self.validate_path(value)
                    if error and not is_safe:
                        violations.append(f"Parameter '{key}': {error}")

            # Recursively check nested structures
            elif isinstance(value, dict):
                is_safe, nested_violations = self.validate_parameters(
                    tool_name, value, allow_warnings
                )
                violations.extend(nested_violations)

            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, (str, dict)):
                        item_dict = (
                            {f"{key}[{i}]": item} if isinstance(item, str) else item
                        )
                        is_safe, item_violations = self.validate_parameters(
                            tool_name, item_dict, allow_warnings
                        )
                        violations.extend(item_violations)

        is_safe = len(violations) == 0
        return is_safe, violations

    def get_rules_by_category(self, category: str) -> List[SafetyRule]:
        """
        Get all safety rules for a specific category.

        Args:
            category: Category name (e.g., "filesystem", "network")

        Returns:
            List of safety rules in the category
        """
        return [rule for rule in self.rules if rule.category == category]

    def get_all_categories(self) -> List[str]:
        """
        Get all safety rule categories.

        Returns:
            List of unique category names
        """
        return list(set(rule.category for rule in self.rules))
