from typing import Literal

from pydantic import BaseModel, ConfigDict


class StringSimilarityConfig(BaseModel):
    """Validated phrase matching configuration."""

    # The model is validated from the phrases section, which also contains
    # settings owned by the Phrases module.
    model_config = ConfigDict(extra="forbid")

    similarity_algorithm: Literal["difflib", "jaro-winkler", "damerau-levenshtein"] = "difflib"
