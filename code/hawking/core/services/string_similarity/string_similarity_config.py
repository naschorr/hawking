from typing import Literal

from pydantic import BaseModel, ConfigDict


class StringSimilarityConfig(BaseModel):
    """Validated core string-matching configuration."""

    model_config = ConfigDict(extra="forbid")

    similarity_algorithm: Literal["difflib", "jaro-winkler", "damerau-levenshtein"] = "difflib"
