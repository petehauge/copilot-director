# Repository Content Copy Instructions

This guide explains how to use the `copy_repo_content.py` script to copy content from one GitHub repository to another.

## Prerequisites

1. **Python 3.7 or higher** installed
2. **Git** installed and available in PATH
3. **GitHub Authentication** - one of the following:
   - GitHub CLI (`gh`) installed and authenticated, OR
   - GitHub Personal Access Token

## Getting a GitHub Token

The script will automatically use your GitHub CLI authentication if available. If you prefer to use a Personal Access Token:

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name (e.g., "Repo Content Copy")
4. Select the following scopes:
   - `repo` (Full control of private repositories)
   - `public_repo` (if only copying public repos)
5. Click "Generate token"
6. **Copy the token immediately** (you won't be able to see it again)

## Installation

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage (with GitHub CLI)

If you have the GitHub CLI installed and authenticated (`gh auth login`), just run:

```bash
python scripts/copy_repo_content.py -s owner/source-repo -d owner/dest-repo
```

### With Environment Variable

Set your GitHub token as an environment variable:

**Windows (PowerShell):**
```powershell
$env:GITHUB_TOKEN = "your_github_token_here"
python scripts/copy_repo_content.py -s owner/source-repo -d owner/dest-repo
```

**Windows (Command Prompt):**
```cmd
set GITHUB_TOKEN=your_github_token_here
python scripts/copy_repo_content.py -s owner/source-repo -d owner/dest-repo
```

**Linux/macOS:**
```bash
export GITHUB_TOKEN="your_github_token_here"
python scripts/copy_repo_content.py -s owner/source-repo -d owner/dest-repo
```

### With Token as Argument

```bash
python scripts/copy_repo_content.py -s owner/source-repo -d owner/dest-repo --token your_github_token_here
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `-s`, `--source` | Source repository in format `owner/repo` (required) |
| `-d`, `--dest` | Destination repository in format `owner/repo` (required) |
| `-t`, `--token` | GitHub personal access token (optional if using `GITHUB_TOKEN` env var or GitHub CLI) |
| `-f`, `--force` | Force copy even if destination repository is not empty |
| `--copy-closed-issues` | Copy closed issues in addition to open issues (default: only open issues) |

### Examples

```bash
# Copy only open issues (default)
python scripts/copy_repo_content.py -s owner/source -d owner/dest

# Copy all issues including closed ones
python scripts/copy_repo_content.py -s owner/source -d owner/dest --copy-closed-issues

# Force copy to non-empty destination
python scripts/copy_repo_content.py -s owner/source -d owner/dest --force
```

## What the Script Does

1. **Copies Source Code:**
   - Clones the source repository to a temporary location
   - Copies all files and directories (excluding .git folder)
   - Preserves file structure and content
   - Cleans up temporary files

2. **Copies Issues:**
   - Fetches open issues from the source repository (or all issues with `--copy-closed-issues`)
   - Creates corresponding issues in the destination repository
   - Preserves issue titles, descriptions, and labels
   - Adds metadata noting the original issue number, author, and URL
   - Maintains open/closed status

## After Running the Script

Once the script completes successfully:

1. Review the copied files in your repository
2. Stage and commit the changes:
   ```bash
   git add .
   git commit -m "Copy content from JediMaster-TerraformSample"
   ```
3. Push to remote:
   ```bash
   git push origin main
   ```

## Troubleshooting

### "GitHub token is required" Error
- Install and authenticate with GitHub CLI: `gh auth login`
- Or set the `GITHUB_TOKEN` environment variable
- Or pass the token via `--token` argument

### "Command failed: git clone"
- Ensure Git is installed and available in your PATH
- Check your internet connection
- Verify the source repository URL is accessible

### "Destination repository is not empty" Error
- The script checks that the destination is empty before copying
- Use `--force` flag to skip this check and copy anyway

### API rate limiting
- GitHub has rate limits for API calls
- Authenticated requests (with token) have higher limits
- If you hit the limit, wait an hour or use a different token

### Permission errors
- Ensure your GitHub token has the correct scopes
- Verify you have write access to the destination repository

## Security Notes

- **Never commit your GitHub token** to the repository
- Use environment variables or secure credential storage
- Tokens should be treated like passwords
- Revoke tokens when no longer needed
- Using GitHub CLI (`gh auth login`) is the most secure option
