from abc import ABC, abstractmethod

class ExecutionStrategy(ABC):
@abstractmethod
def execute(self, prompt, context):
pass

class GeminiStrategy(ExecutionStrategy):
def execute(self, prompt, context): # Gemini logic
pass

class CopilotStrategy(ExecutionStrategy):
def execute(self, prompt, context): # Copilot logic
pass

# @tip: Factory to pick strategy

def get_agent(name):
strategies = {"gemini": GeminiStrategy(), "copilot": CopilotStrategy()}
return strategies.get(name, GeminiStrategy())
