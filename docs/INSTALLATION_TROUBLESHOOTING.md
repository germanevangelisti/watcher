# Installation Troubleshooting

Common issues and solutions when setting up the Watcher Agent development environment.

---

## Backend Installation Issues

### Problem: `make install` hangs on langgraph/langchain

**Symptoms**:
- Installation gets stuck on `langgraph`, `langchain`, or related packages
- Connection reset errors: `Connection aborted.', ConnectionResetError(54, 'Connection reset by peer')`
- No progress for several minutes

**Causes**:
- Large package downloads (langgraph, langchain are 50+ MB combined)
- Network timeouts with PyPI
- Slow or unstable internet connection

**Solutions**:

#### Option 1: Use the phased installation (Recommended)
```bash
make install-backend-fast
```

This installs dependencies in smaller groups, reducing the chance of timeouts.

#### Option 2: Increase pip timeout manually
```bash
cd watcher-monolith/backend
pip install --timeout 100 --retries 10 -r requirements.txt
```

#### Option 3: Install without cache
```bash
cd watcher-monolith/backend
pip install --no-cache-dir -r requirements.txt
```

#### Option 4: Install AI libraries separately
```bash
cd watcher-monolith/backend

# Install everything except AI libraries first
pip install fastapi uvicorn python-dotenv pydantic pytest httpx \
    PyPDF2 pdfplumber sqlalchemy alembic aiosqlite greenlet aiofiles \
    openai tqdm python-multipart python-socketio websockets

# Then install AI libraries with extended timeout
pip install --timeout 200 langgraph langchain langchain-core langchain-openai
```

---

### Problem: Version conflicts with Python dependencies

**Symptoms**:
```
ERROR: pip's dependency resolver does not currently take into account all the packages...
```

**Solutions**:

#### Use a virtual environment (Recommended)
```bash
cd watcher-monolith/backend

# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

#### Upgrade pip and setuptools
```bash
pip install --upgrade pip setuptools wheel
```

---

### Problem: Missing system dependencies for Python packages

**Symptoms**:
- Build errors for `greenlet` or `aiosqlite`
- Missing compiler errors

**Solutions**:

**On macOS:**
```bash
# Install Xcode Command Line Tools
xcode-select --install
```

**On Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3-dev build-essential
```

---

## Frontend Installation Issues

### Problem: `npm install` fails with EACCES errors

**Symptoms**:
```
EACCES: permission denied
```

**Solutions**:

#### Don't use sudo (Best practice)
```bash
cd watcher-monolith/frontend
npm install --no-optional
```

#### If you must, fix npm permissions
```bash
# Reconfigure npm to use a different directory
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

---

### Problem: Node version incompatibility

**Symptoms**:
```
error: The engine "node" is incompatible with this module
```

**Solutions**:

#### Use Node 18 (Recommended)
```bash
# Using nvm (recommended)
nvm install 18
nvm use 18

# Verify
node --version  # Should show v18.x.x
```

---

## Lab Installation Issues

### Problem: Jupyter not starting

**Symptoms**:
- `jupyter lab` command not found
- Kernel errors

**Solutions**:

```bash
cd watcher-lab

# Install jupyter explicitly
pip install jupyterlab

# Start lab
jupyter lab
```

---

## Network/Connectivity Issues

### Problem: PyPI mirrors are slow or unreachable

**Solutions**:

#### Use a faster mirror (China)
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### Use a faster mirror (Europe)
```bash
pip install -r requirements.txt -i https://pypi.org/simple
```

#### Configure pip permanently
Create/edit `~/.pip/pip.conf`:
```ini
[global]
timeout = 100
retries = 10
```

---

## Verification After Installation

### Check backend
```bash
cd watcher-monolith/backend
python -c "import fastapi, langchain, langgraph; print('✅ Backend packages OK')"
```

### Check frontend
```bash
cd watcher-monolith/frontend
npm list --depth=0
```

### Run full verification
```bash
./scripts/verify-sprint0.sh
```

---

## Still Having Issues?

### Clean install (Nuclear option)
```bash
# Backend
cd watcher-monolith/backend
rm -rf venv __pycache__
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Frontend
cd watcher-monolith/frontend
rm -rf node_modules package-lock.json
npm install
```

### Get help
- Check logs: Look for specific error messages
- Verify Python version: `python --version` (should be 3.9+)
- Verify Node version: `node --version` (should be 18.x)
- Check disk space: `df -h`
- Check internet connection: `ping pypi.org`

---

## Quick Reference

| Problem | Quick Fix |
|---------|-----------|
| Install hangs | `make install-backend-fast` |
| Connection errors | `pip install --timeout 100 --retries 10 -r requirements.txt` |
| Version conflicts | Use virtual environment |
| Frontend permissions | Don't use sudo |
| Slow downloads | Use timeout: `--timeout 100` |

---

**Last Updated**: Sprint 0  
**For More Help**: See [AGENTS.md](AGENTS.md) for contribution guidelines
