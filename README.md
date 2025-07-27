# ApexMind Core (v0.1) - Minimal Viable AGI Nucleus

**ApexMind v0.1** is the foundational release of an autonomous agent system designed for safe, hardware-constrained environments. This version establishes the core nervous system for task execution with built-in security constraints using WASI.

```bash
apex execute "find who is the worlds fastest man"
apex execute "read 'documents.txt'"
```

## 🔍 Core Capabilities

- **Secure File Operations**: Read/write with WASI-based permissions
- **Basic Web Interactions**: HTTP/HTTPS requests with safety constraints
- **Command Routing**: Task decomposition and execution
- **Capability-based Security**: Hardware access control
- **Bilingual Support**: English and Russian commands

## 📦 Installation & Build Process

### Step-by-Step Build Windows

```bash
# Clone repository
git clone 'actual link'
cd 'project_root'

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate     # Linux/Mac

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Build WASI security layer
cd wasi_security_layer
maturin develop

# Install core package
cd 'project_root'
pip install -e .

# Install CLI
cd apex-cli
pip install -e .
```

## 🧩 Project Structure

```
apex-mind-build/
├── apex_mind_core/          # Core package
│   ├── common/              # Common types
│   └── core/                # Main modules
│       ├── capability_manifest.py
│       ├── hardware_ops.py
│       ├── orchestrator.py
│       └── wasi_bridge.py
├── apex-cli/                # CLI interface
│   ├── apex.py              # CLI entry point
│   └── manifests/           # Skill definitions
├── manifests/               # Additional manifests
└── wasi_security_layer/     # Rust security core
    ├── src/                 # Rust source
    └── Cargo.toml           # Rust config
```

## 🚀 CLI Usage Guide

### Command Syntax Rules

1. **File Operations**:
   - Read: apex execute "read '<file_path>'"
   - Write: apex execute "write '<file_path>' '<content>'"
2. **Web Operations**:

   - Search: apex execute `search <query>`

3. **Getting to know how to use CLi**

   - apex --help

### Basic Commands

```bash
# Execute a task
apex execute "read '<file_path>'"
apex execute "search latest AI developments"

# View execution history
apex log show
```

### File Operations

```bash
# Read file (allowed paths only)
apex execute "read '<file_path>'"

# Write file (requires manifest permission)
apex execute "write /home/user/status.log 'System operational'"
```

### Web Requests

````bash
# Search web
apex execute "search Raspberry Pi security best practices"

## 🔒 Security Model

v0.1 implements hardware security through:

1. **Capability Manifest** (`manifests/default.json`):

```json
{
  "filesystem": {
    "read": ["/home/user/*", "/var/log/"],
    "write": ["/home/user/output/"]
  },
  "network": {
    "domains": ["example.com", "api.example.com"]
  }
}
````

2. **WASI Validation** - All operations validated against WebAssembly System Interface rules

## 🌐 Language Support

- Commands accepted in **English** and **Russian**
- Automatic language detection based on input
- Example bilingual usage:
  ```bash
  apex execute "read /home/user/data.txt"  # English
  apex execute "прочитать /home/user/data.txt"  # Russian
  ```
