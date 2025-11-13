# Security Policy

## Supported Versions

We actively support and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| < 0.3   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability, please follow these steps:

### 1. **Do NOT** open a public issue

Security vulnerabilities should be reported privately to protect users until a fix is available.

### 2. Email the maintainer

Send an email to **lawrence.carbon@gmail.com** with:
- A clear description of the vulnerability
- Steps to reproduce the issue
- Potential impact and severity
- Any suggested fixes (if you have them)

### 3. Response timeline

- **Initial response**: Within 48 hours
- **Status update**: Within 7 days
- **Fix timeline**: Depends on severity, but we aim for quick resolution

### 4. Disclosure

- We will work with you to coordinate public disclosure
- Credit will be given to the reporter (unless you prefer to remain anonymous)
- A security advisory will be published when the fix is released

## Security Best Practices

When using this tool:

- **API Keys**: Never commit API keys to version control
- **Config Files**: The tool automatically sets secure permissions (600) on config files
- **Command Execution**: Always review generated commands before executing
- **Dependencies**: Keep dependencies up to date (`poetry update`)
- **Environment Variables**: Prefer config files over environment variables for sensitive data

## Known Security Considerations

- **Command Execution**: This tool generates and can execute shell commands. Always review commands before execution, especially with the `--execute` flag.
- **API Keys**: API keys are stored in config files with restricted permissions. Never share your config file.
- **Dependencies**: We regularly update dependencies to include security patches.

## Security Updates

Security updates will be:
- Released as patch versions (e.g., 0.3.1 → 0.3.2)
- Documented in the CHANGELOG.md
- Announced via GitHub releases

Thank you for helping keep QTC secure!

