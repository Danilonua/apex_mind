import logging
from datetime import datetime
from langgraph.graph import StateGraph
class ExecutionTracker:
    def __init__(self):
        self.logger = logging.getLogger("apex_orchestrator")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler('execution_path.log')
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_step(self, node: str, state: dict):
        """Логирует детали выполнения узла"""
        # Обрабатываем разные форматы состояний
        mission = state.get('current_mission', {}).get('content', 'N/A') or state.get('mission', 'N/A')
        safety = state.get('safety_level', 0)
        context = state.get('context', [])
        
        log_msg = (
            f"Узел: {node} | Миссия: {str(mission)[:50]}... | "
            f"Безопасность: Ур.{safety} | Контекст: {len(context)} сообщений"
        )
        self.logger.info(log_msg)
