class Question:
    def __init__(self, text, subreddit, url):
        self._text = text
        self._subreddit = subreddit
        self._url = url
    
    ## Properties

    @property
    def text(self):
        return self._text
    
    @property
    def subreddit(self):
        return self._subreddit

    @property
    def url(self):
        return self._url
