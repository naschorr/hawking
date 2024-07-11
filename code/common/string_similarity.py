from difflib import SequenceMatcher

from common.configuration import Configuration
from common.module.module import Module


class StringSimilarity(Module):

    ## https://stackoverflow.com/questions/17388213/find-the-similarity-metric-between-two-strings
    ## https://stackoverflow.com/questions/6690739/fuzzy-string-comparison-in-python-confused-with-which-library-to-use

    ## Lifecycle
    def __init__(self, config: Configuration, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.similarity_algorithm = config.get("string_similarity_algorithm")

    ## Methods

    @staticmethod
    def _calcJaroWinkleDistance(left: str, right: str):
        raise NotImplementedError(
            "Jaro-Winkle distance calculation hasn't been implemented. Use difflib implementation"
        )


    @staticmethod
    def _calcDamerauLevenshteinDistance(left: str, right: str):
        raise NotImplementedError(
            "Damerau-Levenshtein distance calculation hasn't been implemented. Use difflib implementation"
        )


    @staticmethod
    def _calcDifflibDistance(left: str, right: str):
        return SequenceMatcher(None, left, right).ratio()


    def similarity(self, left: str, right: str):
        if (self.similarity_algorithm == "jaro-winkler"):
            return StringSimilarity._calcJaroWinkleDistance(left, right)
        elif (self.similarity_algorithm == "damerau-levenshtein"):
            return StringSimilarity._calcDamerauLevenshteinDistance(left, right)
        else:
            return StringSimilarity._calcDifflibDistance(left, right)
