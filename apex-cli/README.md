🚀 Apex CLI v0.1

Командный интерфейс для выполнения задач с контролем безопасности. Версия 0.1 предоставляет базовый функционал для работы с файлами, сетью и системными операциями.

## 📋 Основные команды

### 🌐 Глобальные опции

Доступны для всех команд:

- `--version` - Показать версию
- `--log-level LEVEL` - Уровень логирования (debug/info/warning/error)
- `--manifest PATH` - Кастомный файл разрешений
- `--dry-run` - Тестовый режим без выполнения
- `--help` - Показать эту документацию

---

### 🚀 `execute` - Выполнение задач

Главная команда для выполнения пользовательских запросов.

**Синтаксис:**

```bash
apex execute "текст задачи" [опции]
Опции:

--output FILE - Сохранить результат в файл

--input FILE - Прочитать задачу из файла

Примеры:

bash
# Чтение файла
apex execute "Прочитать C:\Users\user\Documents\notes.txt"

# Запись в файл
apex execute "Записать в D:\data\log.txt 'Запись от 2024-07-22'"

# Сетевой запрос с сохранением результата
apex execute "Получить данные с https://api.example.com/status" --output response.txt
🔒 validate - Проверка безопасности
Проверка разрешений для операции без выполнения.

Синтаксис:

bash
apex validate "текст задачи"
Примеры:

bash
# Проверка чтения системного файла
apex validate "Прочитать C:\Windows\system.ini"

# Проверка записи в временную директорию
apex validate "Записать в C:\Temp\test.txt 'hello'"
⚙️ config - Управление конфигурацией
Настройка параметров системы.

Подкоманды:

set - Установить параметр

get - Показать значение параметра

list - Показать все параметры

Доступные ключи:

default_manifest - Путь к манифесту по умолчанию

log_level - Уровень логирования

max_file_size - Максимальный размер файла (МБ)

Примеры:

bash
apex config set default_manifest ./configs/manifest.json
apex config get log_level
apex config list
📜 manifest - Управление разрешениями
Работа с файлами политик безопасности.

Подкоманды:

show - Показать активный манифест

validate - Проверить синтаксис манифеста

generate - Создать шаблон манифеста

Примеры:

bash
apex manifest show
apex manifest validate custom_rules.json
apex manifest generate > template.json
🖥️ system - Системные операции
Управление состоянием системы.

Подкоманды:

status - Показать статус компонентов

clean - Очистить кэш

logs - Показать логи

Опции:

--tail N - Количество строк логов (для system logs)

Примеры:

bash
apex system status
apex system clean
apex system logs --tail 50
🛡️ Манифесты безопасности
Система использует JSON-манифесты для контроля доступа. Пример структуры:

json
{
  "skill_name": "FileReader",
  "filesystem": {
    "read": ["C:/Users/danil/Desktop/apex-test/*"],
    "write": [],
    "delete": []
  },
  "network": false,
  "gpu": false,
  "sensors": false,
  "camera": false
}
Как назначаются манифесты:

Для execute - по названию навыка:

FileReader → manifests/FileReader.json

WebSearch → manifests/WebSearch.json

Для validate - используется manifests/default.json

Можно указать кастомный манифест через --manifest

💻 Пример рабочего сеанса
powershell
# Установка конфигурации
apex config set default_manifest .\security\default.json
apex config set log_level debug

# Проверка манифеста
apex manifest validate .\security\custom_rules.json

# Выполнение задачи
apex execute "Прочитать D:\project\config.yaml" --output config.txt

# Проверка безопасности
apex validate "Записать в C:\Program Files\test.txt 'опасно'"

# Просмотр логов
apex system logs --tail 20
```
