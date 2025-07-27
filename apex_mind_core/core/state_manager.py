from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict, total=False):
    # Базовые обязательные поля
    mission: str
    context: List[str]
    current_step: str
    version: str
    safety_level: int
    capabilities: Dict[str, Any]

    # Дополнительные поля, которые вы используете в тестах / внутри Orchestrator
    current_skill: str
    shader_code: str
    input_data: bytes
    file_path: str
    result: Any
    error: str
    status: str

class StateManager:
    def __init__(self):
        self.state: AgentState = {
            "mission": "",
            "context": [],
            "current_step": "",
            "version": "0.1",
            "safety_level": 1,
            "capabilities": {}
        }

    def update(self, **updates):
        for key, value in updates.items():
            if key in self.state or True:
                self.state[key] = value

    def add_context(self, message: str):
        self.state["context"].append(message)

    def snapshot(self) -> AgentState:
        return self.state.copy()
