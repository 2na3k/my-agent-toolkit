from enum import Enum
from typing import List

class BasedEnum(str, Enum):
    @classmethod
    def as_list(cls) -> List[str]:
        """
        Returns all attribute names (member names) of this Enum.

        Returns:
            List of attribute names
        """
        return [member.name for member in cls]
    
class ModelBasedURL(BasedEnum):
    CLAUDE = "https://api.anthropic.com/v1/"
    GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai/"

class ModelList(BasedEnum):
    CLAUDE = "claude-sonnet-4-5"
    GEMINI = "gemini-3-flash-preview"
    OPENAI = "gpt-5.2"

class ProviderType(BasedEnum):
    CLAUDE = "CLAUDE"
    GEMINI = "GEMINI"
    OPENAI = "OPENAI"
