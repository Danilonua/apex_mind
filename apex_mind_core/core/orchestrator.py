import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import sys
import io


load_dotenv() 
import urllib
from apex_mind_core.core.state_manager import StateManager, AgentState
from apex_mind_core.core.skill_registry import registry
import requests
from apex_mind_core.core.wasi_bridge import (
    ReptilianEngine, 
    HardwareOp, 
    HardwareOpType
)
import os
from wasi_security_layer import (
    validate_file_access,
    validate_gpu_access,
    validate_network_access,
    validate_sensor_access,
    validate_camera_access
)
import json
import logging
import re

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

state_manager = StateManager()


class SecurityEnforcer:
    def __init__(self, skill_name: str):
        self.skill_name = skill_name
        self.manifest_path = f"manifests/{skill_name}.json"
        with open(self.manifest_path) as f:
            self.manifest_json = f.read()
        self.logger = logging.getLogger(f"SecurityEnforcer.{skill_name}")
    
    def check_file_access(self, path: str, operation: str) -> bool:
        try:
            return validate_file_access(path, self.manifest_json)
        except Exception as e:
            self.logger.error(f"File access validation failed: {e}")
            return False
    
    def check_gpu_access(self) -> bool:
        try:
            return validate_gpu_access(self.manifest_json)
        except Exception as e:
            self.logger.error(f"GPU access validation failed: {e}")
            return False
    
    def check_network_access(self) -> bool:
        try:
            return validate_network_access(self.manifest_json)
        except Exception as e:
            self.logger.error(f"Network access validation failed: {e}")
            return False
    
    def check_sensor_access(self) -> bool:
        try:
            return validate_sensor_access(self.manifest_json)
        except Exception as e:
            self.logger.error(f"Sensor access validation failed: {e}")
            return False
    
    def check_camera_access(self) -> bool:
        try:
            return validate_camera_access(self.manifest_json)
        except Exception as e:
            self.logger.error(f"Camera access validation failed: {e}")
            return False

class Orchestrator:
    def __init__(self):
        from .logger import ExecutionTracker
        self.logger = ExecutionTracker()
        self.security_enforcers = {}

    def receive_mission(self, state: dict) -> dict:
        return state

    def limbic_processing(self, state: dict) -> dict:
        return state
    
    def validate_mission(self, mission_text: str) -> str:
        state = {"mission": mission_text}
        try:
            state = self.mission_parser(state)
            parsed = state.get("parsed_command", {})
            
            if not parsed:
                return "Не удалось разобрать команду"
                
            if parsed["target"] == "file":
                path = parsed["path"]
                action = parsed["action"]
                
                enforcer = SecurityEnforcer("default")
                
                if action == "read":
                    if enforcer.check_file_access(path, "read"):
                        return "Операция разрешена"
                    return "Чтение запрещено"
                    
                elif action == "write":
                    if enforcer.check_file_access(path, "write"):
                        return "Операция разрешена"
                    return "Запись запрещена"
            
            elif parsed["target"] == "network":
                if enforcer.check_network_access():
                    return "Операция разрешена"
                return "Сетевой доступ запрещен"
                
            return "Проверка для данного типа операций не реализована"
            
        except Exception as e:
            return f"Ошибка проверки: {str(e)}"

    def mission_parser(self, state: dict) -> dict:
        import re
        mission = state["mission"]
        mission_lower = mission.lower()
        parsed = {"action": None, "target": None, "path": None, "url": None, "query": None}

        action_map = {
            "read": ["прочита", "открой", "покажи", "read", "open", "show"],
            "write": ["запиши", "сохрани", "write", "save"],
            "get": ["найди", "найти", "запрос", "получи", "поиск", "get", "find", "query"],
            "post": ["отправь", "пост", "send", "post"]
        }
        for action, keywords in action_map.items():
            if any(keyword in mission_lower for keyword in keywords):
                parsed["action"] = action
                break

        if parsed["action"] in ("read", "write"):
            m = re.search(r'([A-Za-z]:\\[^\s"\']+)', mission)
            if m:
                parsed["target"] = "file"
                parsed["path"] = m.group(1)

        if parsed["target"] != "file":
            path_match = re.search(r'(?:файл|file)[\s:]+([\'"]?)([^\s\'"]+)\1', mission_lower)
            if path_match:
                parsed["target"] = "file"
                parsed["path"] = path_match.group(2)

        if parsed["action"] == "get":
            parsed["target"] = "network"
            # Убираем ключевые слова из начала
            query = re.sub(
                r'\b(найди|найти|запрос|получи|поиск|get|find|query)\b',
                '',
                mission_lower,
                flags=re.IGNORECASE
            ).strip(' "')
            parsed["query"] = query or mission

        if parsed["target"] == "file":
            if parsed["action"] == "read":
                state["current_skill"] = "FileReader"
            else:
                state["current_skill"] = "FileWriter"
        elif parsed["target"] == "network":
            state["current_skill"] = "WebSearch"
        else:
            state["current_skill"] = "DefaultSkill"

        state["parsed_command"] = parsed
        logger.info(f"Parsed command: {parsed}, selected skill: {state['current_skill']}")
        return state

    def basic_router(self, state: dict) -> dict:
        current_skill = state.get("current_skill")
        action = state.get("parsed_command", {}).get("action")
        target = state.get("parsed_command", {}).get("target")

        if current_skill == "WebSearch" or (action == "get" and target == "network"):
            state["next_node"] = "http_processing"
        elif current_skill in ["FileReader", "FileWriter"]:
            state["next_node"] = "file_ops_processing"
        else:
            logger.debug(f"No direct handler for skill={current_skill}, action={action}, target={target}, fallback to skill execution")

        logger.info(f"Routing to: {state.get('next_node','fallback_skill')}")
        return state

    def file_ops_processing(self, state: dict) -> dict:
        """
        Обработка файловых операций через Reptilian Engine
        с фильтрацией прочитанного содержимого.
        """
        import re

        parsed = state.get("parsed_command", {})
        if not parsed:
            state["error"] = "No parsed command for file operation"
            return state

        action = parsed["action"]
        path = parsed["path"]
        skill_name = state.get("current_skill", "DefaultSkill")
        engine = ReptilianEngine(skill_name)

        try:
            if action == "read":
                op_type = HardwareOpType.FileRead

            elif action == "write":
                op_type = HardwareOpType.FileWrite
                if "data" not in parsed or not parsed["data"]:
                    state["error"] = "No data provided for file write operation"
                    return state
            else:
                state["error"] = f"Unsupported file action: {action}"
                return state

            file_op = HardwareOp(op_type)
            file_op.path = path

            if op_type == HardwareOpType.FileWrite:
                file_op.data = parsed["data"].encode()

            logger.debug(f"Executing file op: {file_op.path}")
            result = engine.execute_hardware_op(file_op)

            if op_type == HardwareOpType.FileRead:
                raw = result.decode('utf-8', errors='replace')
                filtered = re.sub(r'[^ЁёА-Яа-я0-9\s]', '', raw).strip()
                state["result"] = {
                    "type": "file",
                    "content": raw,
                    "filtered": filtered
                }
            else:
                state["result"] = {"type": "file", "status": "written"}

            state["status"] = "completed"
            logger.info(f"File operation completed: {action} {path}")
            print(filtered)

        except PermissionError as e:
            state["error"] = f"Permission denied: {e}"
            logger.error(f"File operation permission error: {e}")
        except Exception as e:
            state["error"] = f"File operation failed: {e}"
            logger.exception("File operation exception")

        return state

    def http_processing(self, state: dict) -> dict:
        parsed = state.get("parsed_command", {})
        
        if parsed.get("query"):
            query = parsed["query"]
        else:
            mission_text = state.get("mission", "")
            query = re.sub(r'най(ти|дите)\s+в\s+интернете', '', mission_text, flags=re.IGNORECASE)
            query = query.strip().strip('"')
        
        query = re.sub(r'[«»"?:]', '', query).strip()
        
        if not query:
            state["error"] = "No search query found"
            return state

        try:
            result_content = self.try_sources(query)
            clean_text = re.sub(r'\s+', ' ', result_content).strip()
            state["result"] = {"type": "http", "status_code": 200, "content": clean_text}
            state["status"] = "completed"
            logger.info(f"Search completed: {query}")
        except Exception as e:
            state["error"] = f"Search operation failed: {e}"
            logger.exception(f"Search processing exception: {e}")
        return state

    def try_sources(self, query: str) -> str:
        sources = [
            self.search_ydc,      # You.com API
            self.search_google,
            lambda q: self._search_wikipedia(q, "ru"),
            lambda q: self._search_wikipedia(q, "en"),
            self.search_ddg
        ]

        if os.getenv("BING_API_KEY"):
            sources.insert(1, self.search_bing) 

        for fn in sources:
            try:
                result = fn(query)
                fn_name = fn.__name__ if hasattr(fn, '__name__') else 'lambda'
                logger.debug(f"Result from {fn_name}: {result[:200]!r}")

                if result and "ничего не найдено" not in result.lower():
                    return result
            except Exception as e:
                logger.warning(f"Source {fn} failed: {e}")

        return "По вашему запросу ничего не найдено"

    def _decode_response(self, res) -> str:
        """Корректно получить текст из байт или Response"""
        if isinstance(res, bytes):
            return res.decode('utf-8', errors='replace')
        if hasattr(res, 'text'):
            return res.text
        return str(res)

    def search_google(self, query: str) -> str:
        q = query.strip().strip('"')
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}&hl=ru"

        op = HardwareOp(HardwareOpType.NetworkRequest)
        op.url = url
        op.method = "GET"
        op.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Cookie": "CONSENT=PENDING+999; SOCS=CAISEwgDEgk1ODE3NDQ3MTEaAnJ1IAEaBgiA_LuUBg"
        }

        res = ReptilianEngine("WebSearch").execute_hardware_op(op)
        raw = self._decode_response(res)
        logger.debug(f"Raw Google: {raw[:300]!r}")

        soup = BeautifulSoup(raw, 'html.parser')
        result = []

        for snippet in soup.select('.V3FYCf, .t2sad, .hgKElc'):
            if text := snippet.get_text(strip=True, separator=' '):
                result.append(text)

        if not result:
            for answer in soup.select('.LGOjhe, .LTKOO, .sW6dbe'):
                if text := answer.get_text(strip=True, separator=' '):
                    result.append(text)

        if not result:
            for container in soup.select('.g'):
                title = container.select_one('h3') or container.select_one('.DKV0Hd')
                snippet = container.select_one('.VwiC3b, .MUxGbd') or container.select_one('.lEBKkf')

                if title and snippet:
                    result.append(f"{title.get_text(strip=True)}: {snippet.get_text(strip=True, separator=' ')}")

        return ' '.join(result[:3]) if result else ""
    

    def search_ydc(self, query: str) -> str:
        api_key = os.getenv("YOU_API_KEY")
        if not api_key:
            return ""
    
        try:
            params = {"query": query}
            encoded_params = urllib.parse.urlencode(params)
            url = f"https://api.ydc-index.io/search?{encoded_params}"
            
            op = HardwareOp(HardwareOpType.NetworkRequest)
            op.url = url
            op.method = "GET"
            op.headers = {
                "X-API-Key": api_key,
                "Accept": "application/json"
            }
    
            res = ReptilianEngine("WebSearch").execute_hardware_op(op)
            raw_response = self._decode_response(res)
            
            if "error" in raw_response:
                error_data = json.loads(raw_response)
                logger.error(f"You.com API error: {error_data.get('error', 'Unknown error')}")
                return ""
            
            response = json.loads(raw_response)
            logger.debug(f"You.com YDC response: {json.dumps(response, ensure_ascii=False)[:500]}")
    
            all_text = []
            for hit in response.get("hits", [])[:5]:  
                if "description" in hit and hit["description"]:
                    all_text.append(hit["description"])
                
                for snippet in hit.get("snippets", []):
                    if snippet.strip():  
                        all_text.append(snippet)
                        
            return " ".join(all_text) if all_text else ""
    
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse You.com response: {e}")
            return ""
        except Exception as e:
            logger.error(f"You.com YDC search failed: {str(e)}")
            return ""
    

    def search_bing(self, query: str) -> str:
        import requests

        subscription_key = os.getenv("BING_API_KEY")
        if not subscription_key:
            raise ValueError("BING_API_KEY не установлен в переменных окружения")

        endpoint = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": subscription_key}
        params = {"q": query, "mkt": "ru-RU"}

        response = requests.get(endpoint, headers=headers, params=params)
        data = response.json()
        logger.debug(f"Raw Bing response: {json.dumps(data, ensure_ascii=False)[:500]}")

        results = []
        if "webPages" in data:
            for item in data["webPages"]["value"][:3]:
                title = item.get("name")
                snippet = item.get("snippet")
                if title and snippet:
                    results.append(f"{title}: {snippet}")

        return ' '.join(results) if results else "По вашему запросу ничего не найдено"

    def _search_wikipedia(self, query: str, lang: str) -> str:
        if lang == "ru":
            query = ' '.join(word.capitalize() for word in query.split())
        elif lang == "en":
            query = self._correct_english_names(query)

        formatted_query = query.replace(' ', '_')
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(formatted_query)}"

        op = HardwareOp(HardwareOpType.NetworkRequest)
        op.url = url
        op.method = "GET"
        op.headers = {
            "User-Agent": "ApexMind/1.0",
            "Accept": "application/json"
        }

        try:
            res = ReptilianEngine("WebSearch").execute_hardware_op(op)
            raw = self._decode_response(res)
            logger.debug(f"Raw Wiki {lang.upper()}: {raw[:300]!r}")

            data = json.loads(raw)
            return data.get("extract", "")
        except Exception as e:
            logger.error(f"Wikipedia error: {e}")
            return ""

    def _correct_english_names(self, text: str) -> str:
        corrections = {
            "илон маск": "Elon Musk",
            "битокин": "Bitcoin",
            "кубик рубика": "Rubik's Cube"
        }

        for ru, en in corrections.items():
            if ru in text.lower():
                return en

        return self._enhanced_transliteration(text)

    def _enhanced_transliteration(self, text: str) -> str:
        translit_map = {
            'илон': 'elon', 'маск': 'musk',
            'битокин': 'bitcoin', 'биткоин': 'bitcoin',
            'рубик': 'rubik', 'кубик': 'cube'
        }

        for ru, en in translit_map.items():
            text = re.sub(rf'\b{ru}\b', en, text, flags=re.IGNORECASE)

        return self._transliterate_ru_en(text)

    def _transliterate_ru_en(self, text: str) -> str:
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        result = []
        for char in text.lower():
            if char in translit_map:
                result.append(translit_map[char])
            elif char in ' -_':
                result.append('_')
            else:
                result.append(char)
        
        return ''.join(result)

    def search_ddg(self, query: str) -> str:
        q = query.strip().strip('"')
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(q)}&format=json&no_html=1"
        op = HardwareOp(HardwareOpType.NetworkRequest)
        op.url = url; op.method = "GET"; op.headers = {"User-Agent": "ApexMind/1.0"}
        res = ReptilianEngine("WebSearch").execute_hardware_op(op)
        raw = self._decode_response(res)
        logger.debug(f"Raw DDG: {raw[:300]!r}")
        data = json.loads(raw or '{}')
        if data.get("AbstractText"): return data["AbstractText"]
        for topic in data.get("RelatedTopics", []):
            if "Text" in topic: return topic["Text"]
            for sub in topic.get("Topics", []):
                if "Text" in sub: return sub["Text"]
        return ""

        
    def conscience_check(self, state: dict) -> dict:
        return state

    def finalize_execution(self, state: dict) -> dict:
        return state

    def executor(self, state: dict) -> dict:
        if not state.get('mission'):
            return {"context": "No mission text provided"}

        try:
            state = self.mission_parser(state)
            state = self.basic_router(state)

            if state.get("next_node") == "file_ops_processing":
                return self.file_ops_processing(state)
            elif state.get("next_node") == "http_processing":
                return self.http_processing(state)
            else:
                # Исполнение навыка через реестр
                result = registry.execute(state['current_skill'], state['mission'])
                return {"current_skill": "completed", "result": result}

        except Exception as e:
            return {"context": f"Execution error: {e}"}

    def analyzer(self, state: dict) -> dict:
        try:
            analysis = registry.execute("SimpleAnalysis", state.get('result', ''))
            return {"current_skill": "analysis_complete", "result": analysis}
        except Exception as e:
            return {"context": f"Analysis error: {e}"}
        
    def register_skill(self, skill_name: str):
        self.security_enforcers[skill_name] = SecurityEnforcer(skill_name)
    
    def execute_operation(self, skill_name: str, operation):
        enforcer = self.security_enforcers.get(skill_name)
        if not enforcer:
            self.logger.error(f"No security enforcer for {skill_name}")
            raise ValueError(f"No security enforcer for {skill_name}")
        
        # Проверка разрешений перед выполнением
        op_type = operation.op_type
        if op_type == HardwareOpType.GpuCompute:
            if not enforcer.check_gpu_access():
                raise PermissionError("GPU access denied")
        
        elif op_type == HardwareOpType.NetworkRequest:
            if not enforcer.check_network_access():
                raise PermissionError("Network access denied")
        
        elif op_type == HardwareOpType.FileRead:
            if not enforcer.check_file_access(operation.path, "read"):
                raise PermissionError(f"Read access to {operation.path} denied")
        
        elif op_type == HardwareOpType.FileWrite:
            if not enforcer.check_file_access(operation.path, "write"):
                raise PermissionError(f"Write access to {operation.path} denied")
        
        elif op_type == HardwareOpType.SensorRead:
            if not enforcer.check_sensor_access():
                raise PermissionError("Sensor access denied")
        
        elif op_type == HardwareOpType.CameraCapture:
            if not enforcer.check_camera_access():
                raise PermissionError("Camera access denied")
        
        return ReptilianEngine(skill_name).execute_hardware_op(operation)