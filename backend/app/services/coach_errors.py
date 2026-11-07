class ChatError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)
