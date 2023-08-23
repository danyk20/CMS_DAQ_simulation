class ValidationError(Exception):
    """
    Custom Error that occurs when MOM envelope validation fails
    """
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors
