#!/usr/bin/env python3
# apex.py

import shutil
import typer
from typing import List, Optional
import os
import sys
import json
import logging
import textwrap
from apex_mind_core.core.orchestrator import Orchestrator
from apex_mind_core.core.wasi_bridge import WASIGuard, HardwareOp, HardwareOpType
import sys

sys.path.append("C:/Users/danil/Desktop/apex-mind-core_v0.1")
orchestrator = Orchestrator()
app = typer.Typer()

# Глобальный контекст для хранения состояния
class GlobalContext:
    def __init__(self):
        self.log_level = "info"
        self.manifest = None
        self.dry_run = False
        self.config_path = os.path.expanduser("~/.apex/config.json")
        self.log_path = os.path.expanduser("~/.apex/logs/apex.log")
        self.config = {}
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                self.log_level = self.config.get("log_level", "info")
                self.manifest = self.config.get("default_manifest")
        except Exception as e:
            logging.error(f"Ошибка загрузки конфига: {e}")
            self.config = {}

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

def show_full_help():
    """Показать полную справку из README.md"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        readme_path = os.path.join(base_dir, 'README.md')
        
        if not os.path.exists(readme_path):
            typer.echo("Файл документации не найден!")
            return
            
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
            typer.echo(content)
    except Exception as e:
        typer.echo(f"Ошибка показа документации: {e}", err=True)

def show_quick_help():
    """Показать краткую справку по командам"""
    help_text = """
    🚀 Apex CLI v0.1 - Безопасное выполнение задач

    Основные команды:
      execute    Выполнение пользовательских задач
      validate   Проверка безопасности операций
      config     Управление конфигурацией системы
      manifest   Работа с файлами разрешений
      system     Системные операции

    Глобальные опции:
      --version         Показать версию
      --log-level LEVEL Уровень логирования (debug/info/warning/error)
      --manifest PATH   Кастомный файл разрешений
      --dry-run         Тестовый режим без выполнения
      --help            Краткая справка
      --full-help       Полная документация

    Примеры:
      apex execute "Прочитать файл.txt"
      apex validate "Записать в системный файл"
      apex config set log_level debug

    Для подробной справки по команде:
      apex <команда> --help
      apex --full-help для полной документации
    """
    typer.echo(textwrap.dedent(help_text).strip())

# Callback для глобальных опций
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
         False, "--version", help="Показать версию", is_eager=True
     ),
     full_help: bool = typer.Option(
         False, "--full-help", help="Показать полную документацию", is_eager=True
     ),
    log_level: str = typer.Option(None, "--log-level", help="Уровень логирования (debug/info/warning/error)"),
    manifest: str = typer.Option(None, "--manifest", help="Кастомный файл разрешений"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Тестовый режим без выполнения"),
    help: bool = typer.Option(
         False, "--help", "-h", help="Показать краткую справку", is_eager=True
     ),
):
    # Обработка запросов справки
    if help or (not any([version, full_help, log_level, manifest, dry_run]) and ctx.invoked_subcommand is None):
        show_quick_help()
        raise typer.Exit()
    
    if version:
        typer.echo("Apex CLI v0.1")
        raise typer.Exit()
    
    if full_help:
        show_full_help()
        raise typer.Exit()
    
    ctx.obj = GlobalContext()
    
    if log_level:
        ctx.obj.log_level = log_level.lower()
    
    if manifest:
        ctx.obj.manifest = manifest
    
    if dry_run:
        ctx.obj.dry_run = True
    
    # Настройка логирования
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR
    }
    logging.basicConfig(
        level=log_levels.get(ctx.obj.log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(ctx.obj.log_path),
            logging.StreamHandler()
        ]
    )

# Команда execute
@app.command()
def execute(
    ctx: typer.Context,
    task: Optional[str] = typer.Argument(None, help="Текст задачи"),
    output: Optional[str] = typer.Option(None, "--output", help="Сохранить результат в файл"),
    input: Optional[str] = typer.Option(None, "--input", help="Прочитать задачу из файла"),
):
    """
    Выполнение пользовательских запросов
    
    Примеры:
      apex execute "Прочитать файл.txt"
      apex execute "Записать в log.txt 'текст'" --output result.txt
      apex execute --input task.txt
    """
    if input:
        try:
            with open(input, 'r', encoding='utf-8') as f:
                task_text = f.read()
        except Exception as e:
            typer.echo(f"Ошибка чтения файла: {e}", err=True)
            raise typer.Exit(code=1)
    elif task:
        task_text = task
    else:
        typer.echo("Не указана задача!", err=True)
        raise typer.Exit(code=1)
    
    if ctx.obj.dry_run:
        typer.echo(f"[DRY-RUN] Выполнение: {task_text}")
        if output:
            typer.echo(f"[DRY-RUN] Результат будет сохранен в: {output}")
        return
    
    try:
        result = orchestrator.executor({
            "current_step": "WebSearch",
            "mission": task_text
        })
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(str(result))
            typer.echo(f"✅ Результат сохранен в {output}")
        else:
            typer.echo(result)
            
    except Exception as e:
        logging.error(f"Ошибка выполнения: {e}")
        typer.echo(f"❌ [ERROR] {e}", err=True)
        raise typer.Exit(code=2)

# Команда validate
@app.command()
def validate(
    ctx: typer.Context,
    task: str = typer.Argument(..., help="Текст задачи для проверки"),
):
    """
    Проверка безопасности операции
    
    Примеры:
      apex validate "Прочитать C:\Windows\system.ini"
      apex validate "Записать в C:\Temp\test.txt 'hello'"
    """
    try:
        # Парсинг команды
        state = {"mission": task}
        state = orchestrator.mission_parser(state)
        parsed = state["parsed_command"]
        
        # Проверка разрешений
        if parsed["target"] == "file":
            path = parsed["path"]
            guard = WASIGuard(ctx.obj.manifest or "manifests/default.json")
            if parsed["action"] == "read":
                if guard.file_ops._check_permission("read", path):
                    typer.echo("🟢 [SECURITY] Операция разрешена")
                else:
                    typer.echo(f"🔴 [SECURITY] Операция запрещена: чтение {path}")
            elif parsed["action"] == "write":
                if guard.file_ops._check_permission("write", path):
                    typer.echo("🟢 [SECURITY] Операция разрешена")
                else:
                    typer.echo(f"🔴 [SECURITY] Операция запрещена: запись в {path}")
        else:
            typer.echo("⚠️ [SECURITY] Проверка для сетевых операций не реализована")
            
    except Exception as e:
        typer.echo(f"❌ Ошибка валидации: {e}", err=True)
        raise typer.Exit(code=3)

# Группа команд config
config_app = typer.Typer()
app.add_typer(config_app, name="config", help="Управление конфигурацией")

@config_app.command("set")
def config_set(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Ключ параметра"),
    value: str = typer.Argument(..., help="Значение параметра"),
):
    """
    Установить параметр конфигурации
    
    Пример:
      apex config set default_manifest ./configs/manifest.json
    """
    valid_keys = ["default_manifest", "log_level", "max_file_size"]
    if key not in valid_keys:
        typer.echo(f"❌ Недопустимый ключ: {key}", err=True)
        typer.echo(f"✅ Допустимые ключи: {', '.join(valid_keys)}")
        raise typer.Exit(code=1)
    
    ctx.obj.config[key] = value
    ctx.obj.save_config()
    typer.echo(f"✅ Параметр '{key}' установлен в '{value}'")

@config_app.command("get")
def config_get(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Ключ параметра"),
):
    """
    Показать значение параметра
    
    Пример:
      apex config get log_level
    """
    value = ctx.obj.config.get(key, "Не установлено")
    typer.echo(f"{key} = {value}")

@config_app.command("list")
def config_list(ctx: typer.Context):
    """
    Показать все параметры конфигурации
    
    Пример:
      apex config list
    """
    for key, value in ctx.obj.config.items():
        typer.echo(f"{key} = {value}")

# Группа команд manifest
manifest_app = typer.Typer()
app.add_typer(manifest_app, name="manifest", help="Управление разрешениями")

@manifest_app.command("show")
def manifest_show(ctx: typer.Context):
    """
    Показать активный манифест
    
    Пример:
      apex manifest show
    """
    manifest_path = ctx.obj.manifest or ctx.obj.config.get("default_manifest") or "manifests/default.json"
    try:
        with open(manifest_path, 'r') as f:
            content = f.read()
            typer.echo(content)
    except Exception as e:
        typer.echo(f"❌ Ошибка чтения манифеста: {e}", err=True)
        raise typer.Exit(code=4)

@manifest_app.command("validate")
def manifest_validate(
    ctx: typer.Context,
    file: str = typer.Argument(..., help="Путь к файлу манифеста"),
):
    """
    Проверить синтаксис манифеста
    
    Пример:
      apex manifest validate custom_rules.json
    """
    try:
        with open(file, 'r') as f:
            manifest = json.load(f)
        # Простая проверка структуры
        required_sections = ["filesystem", "network", "gpu"]
        for section in required_sections:
            if section not in manifest:
                typer.echo(f"❌ [INVALID] Отсутствует секция: {section}", err=True)
                raise typer.Exit(code=5)
        typer.echo("🟢 [VALID] Синтаксис манифеста корректный")
    except Exception as e:
        typer.echo(f"❌ Ошибка валидации: {e}", err=True)
        raise typer.Exit(code=5)

@manifest_app.command("generate")
def manifest_generate(ctx: typer.Context):
    """
    Создать шаблон манифеста
    
    Пример:
      apex manifest generate > custom_manifest.json
    """
    template = {
        "skill_name": "default",
        "filesystem": {
            "read": ["/safe/path/*"],
            "write": ["/output/dir/"],
            "delete": []
        },
        "network": True,
        "gpu": False,
        "sensors": False,
        "camera": False
    }
    typer.echo(json.dumps(template, indent=2))

# Группа команд system
system_app = typer.Typer()
app.add_typer(system_app, name="system", help="Системные операции")

@system_app.command("status")
def system_status(ctx: typer.Context):
    """
    Показать статус компонентов
    
    Пример:
      apex system status
    """
    status = {
        "core": "active",
        "security": "enabled",
        "network": "available",
        "storage": f"{shutil.disk_usage('/').free / 1024**3:.1f} GB свободно"
    }
    for component, state in status.items():
        typer.echo(f"{component}: {state}")

@system_app.command("clean")
def system_clean(ctx: typer.Context):
    """
    Очистить кэш и временные файлы
    
    Пример:
      apex system clean
    """
    cache_dir = os.path.expanduser("~/.apex/cache")
    try:
        os.makedirs(cache_dir, exist_ok=True)
        count = 0
        for file in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
                count += 1
        typer.echo(f"✅ Очищено файлов: {count} в {cache_dir}")
    except Exception as e:
        typer.echo(f"❌ Ошибка очистки: {e}", err=True)
        raise typer.Exit(code=6)

@system_app.command("logs")
def system_logs(
    ctx: typer.Context,
    tail: int = typer.Option(20, "--tail", help="Количество последних строк"),
):
    """
    Показать последние логи
    
    Пример:
      apex system logs
      apex system logs --tail 50
    """
    try:
        if not os.path.exists(ctx.obj.log_path):
            typer.echo("Файл логов не найден")
            return
            
        with open(ctx.obj.log_path, 'r') as f:
            lines = f.readlines()[-tail:]
            typer.echo("".join(lines))
    except Exception as e:
        typer.echo(f"❌ Ошибка чтения логов: {e}", err=True)
        raise typer.Exit(code=7)

if __name__ == "__main__":
    app()