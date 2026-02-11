# Environment Setup Guide

## Configuration Files

The Watcher Agent system uses environment variables for configuration. Since `.env` files are git-ignored, use this guide to set up your environment.

> **Note**: A `.env.example` file should exist in `watcher-monolith/backend/` but may not be present due to git ignore rules. Use the template below instead.

### Backend Configuration

Create a `.env` file in `watcher-monolith/backend/` with the following variables:

```bash
# OpenAI API Configuration
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your-openai-api-key-here

# Watcher Service Configuration
MAX_RETRIES=3
MAX_FRAGMENT_SIZE=2000

# Optional: Model Configuration
# MODEL=gpt-3.5-turbo

# Optional: Rate Limiting
# MAX_TOKENS_PER_MINUTE=80000
# REQUESTS_PER_MINUTE=60
```

### Important Notes

1. **OPENAI_API_KEY**: Required for AI-powered analysis features. The system will run with fallback responses if not configured.
2. **Graceful Degradation**: The backend will start successfully even without an API key, showing warnings in logs.
3. **Security**: Never commit `.env` files or API keys to the repository.

### Quick Setup

```bash
# Copy the example (if available)
cp watcher-monolith/backend/.env.example watcher-monolith/backend/.env

# Edit with your actual values
nano watcher-monolith/backend/.env
```

### Verification

Run the backend configuration check:

```bash
cd watcher-monolith/backend
python check_config.py
```

This will verify that your environment is properly configured.
