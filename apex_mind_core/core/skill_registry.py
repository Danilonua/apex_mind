from pydantic import BaseModel
from typing import Callable, Dict, Any
from apex_mind_core.core.capability_registry import CapabilityRegistry

cap_reg = CapabilityRegistry()

class Skill(BaseModel):
    name: str
    description: str
    function: Callable[[str], str]
    input_schema: Dict[str, Any] = {}
    required_capabilities: list = []

class SecureSkillRegistry:
    def __init__(self):
        self.skills = {}
        
    def register(self, skill: Skill):
        self.skills[skill.name] = skill
        
    def execute(self, skill_name: str, input_data: str) -> str:
        skill = self.skills.get(skill_name)
        if not skill:
            return f"Error: Skill '{skill_name}' not found"
            
        # Check capabilities
        if not all(cap_reg.check_capability(cap) for cap in skill.required_capabilities):
            return "Permission denied: Missing capabilities"
            
        return skill.function(input_data)

# Initialize registry
registry = SecureSkillRegistry()

# Skill decorator with capability requirements
def skill_decorator(name: str, desc: str, capabilities: list):
    def decorator(func):
        registry.register(Skill(
            name=name,
            description=desc,
            function=func,
            required_capabilities=capabilities
        ))
        return func
    return decorator

# Tier 1 Basic Skills
@skill_decorator(
    name="WebSearch",
    desc="Perform web search queries",
    capabilities=["WebSearch"]
)
def web_search(query: str) -> str:
    return f"Web search results for: {query}"

@skill_decorator(
    name="FileRead",
    desc="Read files from allowed paths",
    capabilities=["FileRead"]
)
def file_read(path: str) -> str:
    if not cap_reg.check_capability("FileRead", path):
        return "Permission denied"
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"
    
@skill_decorator(
    name="DefaultSkill",
    desc="Fallback skill for unknown commands",
    capabilities=[]
)
def default_skill(query: str) -> str:
    return f"Команда не распознана. Попытка выполнить запрос: {query}"


@skill_decorator(
    name="SimpleAnalysis",
    desc="Advanced data analysis with statistics",
    capabilities=[]
)
def analyze_file_content(data: str) -> str:
    """Анализирует содержимое файла и возвращает статистику"""
    lines = data.split('\n')
    word_count = sum(len(line.split()) for line in lines)
    char_count = sum(len(line) for line in lines)
    
    stats = (
        f"Анализ завершён:\n"
        f"• Строк: {len(lines)}\n"
        f"• Слов: {word_count}\n"
        f"• Символов: {char_count}"
    )
    return stats
