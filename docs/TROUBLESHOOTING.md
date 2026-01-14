# Troubleshooting Guide

Common issues and solutions for QTC.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Issues](#configuration-issues)
- [API Issues](#api-issues)
- [Command Generation Issues](#command-generation-issues)
- [Performance Issues](#performance-issues)
- [General Issues](#general-issues)

## Installation Issues

### Poetry Not Found

**Problem:** `poetry: command not found`

**Solution:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"
```

### Python Version Too Old

**Problem:** `Python 3.12+ required`

**Solution:**
- Install Python 3.12 or newer
- Use `pyenv` to manage Python versions:
```bash
pyenv install 3.12.0
pyenv local 3.12.0
```

## Configuration Issues

### No API Key Configured

**Problem:** `Failed to configure API key`

**Solution:**
```bash
qtc config providers set
```

Follow the prompts to configure your LLM provider.

### Config File Permission Error

**Problem:** `Permission denied` when accessing config

**Solution:**
```bash
# Check permissions
ls -la ~/.config/cli-nlp/

# Fix permissions
chmod 600 ~/.config/cli-nlp/config.json
```

### Invalid Config File

**Problem:** `Invalid JSON in config file`

**Solution:**
1. Backup current config:
```bash
cp ~/.config/cli-nlp/config.json ~/.config/cli-nlp/config.json.bak
```

2. Reset config:
```bash
rm ~/.config/cli-nlp/config.json
qtc config providers set
```

## API Issues

### API Rate Limit Exceeded

**Problem:** `Rate limit exceeded` errors

**Solution:**
- Wait before retrying
- Use caching (enabled by default)
- Consider using a different provider
- Check your API quota

### API Key Invalid

**Problem:** `Invalid API key`

**Solution:**
1. Verify your API key:
```bash
qtc config show
```

2. Update API key:
```bash
qtc config providers set
```

3. Check environment variables:
```bash
echo $OPENAI_API_KEY  # or your provider's key
```

### Network Timeout

**Problem:** `Connection timeout` or `Request timeout`

**Solution:**
- Check internet connection
- Verify firewall settings
- Try again (automatic retry is enabled)
- Use `--verbose` to see detailed errors

## Command Generation Issues

### Empty Response

**Problem:** Command generation returns empty

**Solution:**
1. Check verbose output:
```bash
qtc --verbose "your query"
```

2. Check logs:
```bash
qtc --log-file debug.log "your query"
```

3. Try a simpler query
4. Check API status

### Invalid Command Generated

**Problem:** Generated command doesn't work

**Solution:**
1. Use refinement mode:
```bash
qtc --refine "your query"
```

2. Use alternatives:
```bash
qtc --alternatives "your query"
```

3. Edit before execution:
```bash
qtc --edit "your query"
```

### Command Too Complex

**Problem:** Generated command is too complex or incorrect

**Solution:**
- Break down into smaller queries
- Use refinement mode
- Provide more context in query
- Use multi-command support for complex operations

## Performance Issues

### Slow Command Generation

**Problem:** Commands take too long to generate

**Solution:**
1. Check cache hit rate:
```bash
qtc stats
```

2. Enable caching (default):
```bash
# Caching is enabled by default
```

3. Use a faster model:
```bash
qtc config model gpt-4o-mini  # Faster, cheaper
```

4. Check network latency

### High Memory Usage

**Problem:** QTC uses too much memory

**Solution:**
1. Clear cache:
```bash
qtc cache clear
```

2. Clear history:
```bash
qtc history clear
```

3. Reduce cache TTL in config

## General Issues

### Command Not Found

**Problem:** `qtc: command not found`

**Solution:**
```bash
# Install in development mode
poetry install

# Or add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Permission Denied

**Problem:** Permission errors when writing files

**Solution:**
```bash
# Check directory permissions
ls -la ~/.local/share/cli-nlp/
ls -la ~/.cache/cli-nlp/

# Fix permissions
chmod -R 755 ~/.local/share/cli-nlp/
chmod -R 755 ~/.cache/cli-nlp/
```

### Debugging

**Enable Debug Mode:**
```bash
qtc --debug "your query"
```

**View Logs:**
```bash
qtc --log-file debug.log "your query"
cat debug.log
```

**Check Metrics:**
```bash
qtc metrics show
qtc stats
```

### Getting Help

1. Check verbose output:
```bash
qtc --verbose "your query"
```

2. Check logs:
```bash
qtc --log-file debug.log "your query"
```

3. View metrics:
```bash
qtc metrics show --json
```

4. Check GitHub issues:
   - Search existing issues
   - Create new issue with:
     - Error message
     - Verbose output
     - System information
     - Steps to reproduce

## Common Error Messages

### "LiteLLM package not installed"

**Solution:**
```bash
poetry install
```

### "Failed to read cache file"

**Solution:**
```bash
# Clear corrupted cache
rm ~/.cache/cli-nlp/command_cache.json
```

### "Invalid JSON response from API"

**Solution:**
- Try again (may be transient)
- Use a different model
- Check API status
- Report issue if persistent

### "Empty response from API"

**Solution:**
- Check API key
- Check API quota
- Try again
- Use verbose mode for details

## Performance Tips

1. **Use Caching:** Enabled by default, significantly speeds up repeated queries

2. **Choose Right Model:** Faster models (gpt-4o-mini) for simple queries, powerful models for complex ones

3. **Batch Operations:** Use `qtc batch` for multiple queries

4. **Templates:** Save common commands as templates

5. **History:** Use history to quickly reuse commands

## Still Having Issues?

1. Enable debug mode: `qtc --debug "query"`
2. Check logs: `qtc --log-file debug.log "query"`
3. View metrics: `qtc metrics show`
4. Check GitHub issues
5. Create new issue with:
   - Error message
   - Debug output
   - System info
   - Steps to reproduce
