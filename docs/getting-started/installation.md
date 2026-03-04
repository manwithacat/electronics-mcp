# Installation

## Prerequisites

- **Python 3.12+**
- **Ngspice** (the SPICE simulation engine)

### Install Ngspice

=== "macOS"

    ```bash
    brew install ngspice
    ```

=== "Ubuntu/Debian"

    ```bash
    sudo apt-get install ngspice
    ```

=== "Windows"

    Download from [ngspice.sourceforge.io](https://ngspice.sourceforge.io/download.html) and add to PATH.

## Install ElectronicsMCP

```bash
pip install electronics-mcp
```

Or install from source:

```bash
git clone https://github.com/manwithacat/electronics-mcp.git
cd electronics-mcp
pip install -e ".[dev,web]"
```

## Configure Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "electronics": {
      "command": "python",
      "args": ["-m", "electronics_mcp.mcp.server"],
      "cwd": "."
    }
  }
}
```

## Verify Installation

```bash
# Check ngspice
ngspice --version

# Check Python package
python -c "import electronics_mcp; print('OK')"

# Initialize a project database
python -m electronics_mcp.mcp.server --init
```

## Optional: Web UI

For the interactive parameter explorer and waveform viewer:

```bash
pip install electronics-mcp[web]
python -m electronics_mcp.web.run
# Opens at http://localhost:8080
```
