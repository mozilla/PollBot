class TaskError(Exception):
    def __init__(self, message, *, url=None):
        super().__init__(message)
        self.url = url
