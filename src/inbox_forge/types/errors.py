class DuplicateEmailError(Exception):
    """Raised when attempting to parse a duplicate email."""

    pass


class SearchError(Exception):
    """Raised when there is an error with the search engine."""

    pass
