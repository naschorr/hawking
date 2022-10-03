from difflib import SequenceMatcher

from common.configuration import Configuration

## Config
CONFIG_OPTIONS = Configuration.load_config()


class StringSimilarity:
    ## https://stackoverflow.com/questions/17388213/find-the-similarity-metric-between-two-strings
    ## https://stackoverflow.com/questions/6690739/fuzzy-string-comparison-in-python-confused-with-which-library-to-use

    @staticmethod
    def _calcJaroWinkleDistance(stringA, stringB):
        raise NotImplementedError(
            "Jaro-Winkle distance calculation hasn't been implemented. Use difflib implementation"
        )

    @staticmethod
    def _calcDamerauLevenshteinDistance(stringA, stringB):
        raise NotImplementedError(
            "Damerau-Levenshtein distance calculation hasn't been implemented. Use difflib implementation"
        )

    @staticmethod
    def _calcDifflibDistance(stringA, stringB):
        return SequenceMatcher(None, stringA, stringB).ratio()

    @staticmethod
    def similarity(stringA, stringB):
        similarity_algorithm = CONFIG_OPTIONS.get("string_similarity_algorithm")

        if (similarity_algorithm == "jaro-winkler"):
            return StringSimilarity._calcJaroWinkleDistance(stringA, stringB)
        elif (similarity_algorithm == "damerau–levenshtein"):
            return StringSimilarity._calcDamerauLevenshteinDistance(stringA, stringB)
        else:
            return StringSimilarity._calcDifflibDistance(stringA, stringB)