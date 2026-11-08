class ChatError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


class PlanGenerationError(ChatError):
    def __init__(self, status, message, code, reference, issues=None):
        super().__init__(status, message)
        self.code, self.reference, self.issues = code, reference, issues or []

    def detail(self):
        return {'message':self.message, 'code':self.code, 'reference':self.reference,
                'issues':self.issues, 'plan_generated':False}
