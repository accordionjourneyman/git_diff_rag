#!/usr/bin/env bash
# ============================================================================
# Git Diff RAG - Bash Wrapper (DEPRECATED)
# ============================================================================
# 
# ⚠️  DEPRECATION NOTICE:
# This bash script is deprecated and maintained only for backward compatibility.
# Please use the new Python CLI instead:
# 
#   python cli.py analyze --repo <repo_name> [OPTIONS]
# 
# The Python CLI provides:
#   - Cross-platform support (Windows, macOS, Linux)
#   - Better error messages and debugging
#   - Direct Python integration (no subprocess overhead)
#   - Easier testing and maintenance
# 
# This script now delegates to the Python CLI.
# ============================================================================

set -euo pipefail

# Get script directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Find Python
PYTHON_CMD="python3"
if [[ -f "$PROJECT_ROOT/.venv/bin/python3" ]]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python3"
elif [[ -f "$PROJECT_ROOT/venv/bin/python3" ]]; then
    PYTHON_CMD="$PROJECT_ROOT/venv/bin/python3"
fi

# Delegate to Python CLI
exec "$PYTHON_CMD" "$PROJECT_ROOT/cli.py" analyze "$@"

show_help() {
    cat << 'EOF'
Git Diff RAG - Repository-driven LLM workflow orchestrator

USAGE:
    ./scripts/New-Bundle.sh --repo <repo_name> [OPTIONS]

REQUIRED:
    --repo <name>       Repository name (must match repository-setup/<name>.md)

OPTIONS:
    --workflow <name>   Workflow to execute (default: from config's default_workflow)
    --target <ref>      Base reference for diff (default: config.remote/config.main_branch)
    --source <ref>      Tip reference for diff (default: HEAD)
    --commit <sha>      Analyze a specific commit (equivalent to --target sha~1 --source sha)
    --language <lang>   Force specific language context (e.g., python, sql) for this layer
    --dry-run, -n       Render prompt, check tokens, and exit without calling LLM (Validation Gate)
    --output-format <fmt> JSON or Markdown (default: markdown)
    --debug             Enable verbose debug output
    --help, -h          Show this help message

EXAMPLES:
    # Dry run validation
    ./scripts/New-Bundle.sh --repo myrepo --dry-run

    # Analyze a specific commit
    ./scripts/New-Bundle.sh --repo myrepo --commit 8f3a2b1

    # Compare specific branches
    ./scripts/New-Bundle.sh --repo myrepo --target main --source feature-branch

    # JSON output workflow
    ./scripts/New-Bundle.sh --repo myrepo --output-format json

CONFIGURATION:
    Repository configs are in repository-setup/<repo_name>.md with YAML frontmatter.
EOF
    exit 0
}

usage() {
    echo "Usage: $0 --repo <repo_name> [--workflow <name>] [--dry-run] [--output-format <fmt>]"
    echo "Run '$0 --help' for more information."
    exit 1
}

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
    exit 1
}

debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] [DEBUG] $1"
    fi
}

get_config() {
    local file="$1"
    local query="$2"
    python3 -c "import yaml, sys; docs=list(yaml.safe_load_all(open('$file'))); print(docs[0]$query)" 2>/dev/null || echo "None"
}

# ----------------------------------------------------------------------------
# Argument Parsing
# ----------------------------------------------------------------------------

REPO_NAME=""
WORKFLOW=""
DEBUG="false"
DRY_RUN="false"
OUTPUT_FORMAT="markdown"
CLI_TARGET=""
CLI_SOURCE=""
CLI_COMMIT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo) REPO_NAME="$2"; shift 2 ;;
        --workflow) WORKFLOW="$2"; shift 2 ;;
        --target) CLI_TARGET="$2"; shift 2 ;;
        --source) CLI_SOURCE="$2"; shift 2 ;;
        --commit) CLI_COMMIT="$2"; shift 2 ;;
        --language) export CODE_LANGUAGE="$2"; shift 2 ;;
        --dry-run|-n) DRY_RUN="true"; shift ;;
        --output-format|-o) OUTPUT_FORMAT="$2"; shift 2 ;;
        --debug) DEBUG="true"; shift ;;
        --help|-h) show_help ;;
        *) usage ;;
    esac
done

if [[ -z "$REPO_NAME" ]]; then usage; fi

# Pass Output Format to Python scripts
export OUTPUT_FORMAT

# ----------------------------------------------------------------------------
# Config Loading
# ----------------------------------------------------------------------------

SETUP_FILE="repository-setup/${REPO_NAME}.md"
if [[ ! -f "$SETUP_FILE" ]]; then
    error "Repository setup file not found: $SETUP_FILE"
fi

REPO_PATH=$(get_config "$SETUP_FILE" "['path']")
MAIN_BRANCH=$(get_config "$SETUP_FILE" ".get('main_branch', 'main')")
REMOTE=$(get_config "$SETUP_FILE" ".get('remote', 'origin')")

if [[ -z "$WORKFLOW" ]]; then
    WORKFLOW=$(get_config "$SETUP_FILE" ".get('default_workflow', 'pr_review')")
fi

log "Target: $REPO_NAME ($REPO_PATH)"
log "Workflow: $WORKFLOW"
log "Mode: $([[ "$DRY_RUN" == "true" ]] && echo 'DRY RUN' || echo 'LIVE')"

# ----------------------------------------------------------------------------
# Safeguards
# ----------------------------------------------------------------------------

if [[ ! -d "$REPO_PATH/.git" ]]; then
    error "Not a git repository: $REPO_PATH"
fi

if [[ -n "$(git -C "$REPO_PATH" status --porcelain)" ]]; then
    error "Uncommitted changes detected in $REPO_PATH. Please commit or stash first."
fi

# ----------------------------------------------------------------------------
# Workflow Execution
# ----------------------------------------------------------------------------

WF_PROMPT=$(get_config "$SETUP_FILE" ".get('$WORKFLOW', {}).get('prompt')")
WF_LLM=$(get_config "$SETUP_FILE" ".get('$WORKFLOW', {}).get('llm', 'copilot')")
WF_MODEL=$(get_config "$SETUP_FILE" ".get('$WORKFLOW', {}).get('model', 'gemini-1.5-flash')" || echo "gemini-1.5-flash")
POST_STEPS=$(get_config "$SETUP_FILE" ".get('$WORKFLOW', {}).get('post_steps')")

if [[ "$WF_PROMPT" == "None" ]]; then
    error "Workflow '$WORKFLOW' not defined or missing 'prompt' in $SETUP_FILE"
fi

# Generate Diff
# Determine Target (Base)
if [[ -n "$CLI_TARGET" ]]; then
    TARGET_REF="$CLI_TARGET"
elif [[ -n "$CLI_COMMIT" ]]; then
    TARGET_REF="$CLI_COMMIT~1"
else
    TARGET_REF="$([ -n "$REMOTE" ] && echo "$REMOTE/$MAIN_BRANCH" || echo "$MAIN_BRANCH")"
fi

# Determine Source (Tip)
if [[ -n "$CLI_SOURCE" ]]; then
    SOURCE_REF="$CLI_SOURCE"
elif [[ -n "$CLI_COMMIT" ]]; then
    SOURCE_REF="$CLI_COMMIT"
else
    SOURCE_REF="HEAD"
fi

log "Generating git diff: $TARGET_REF...$SOURCE_REF"

if ! git -C "$REPO_PATH" rev-parse --verify "$TARGET_REF" &>/dev/null; then
    log "Ref $TARGET_REF not found locally. Assuming local-only or fetch needed."
fi

DIFF_CONTENT=$(git -C "$REPO_PATH" diff "$TARGET_REF...$SOURCE_REF")

if [[ -z "$DIFF_CONTENT" ]]; then
    log "No changes detected. Skipping LLM call."
    exit 0
fi

# Output Bundle setup
TIMESTAMP=$(date +"%Y%m%dT%H%M%S")
OUTPUT_DIR="output/${TIMESTAMP}-${REPO_NAME}-${WORKFLOW}"
mkdir -p "$OUTPUT_DIR"
log "Output directory: $OUTPUT_DIR"

# Save Raw Diff
echo "$DIFF_CONTENT" > "$OUTPUT_DIR/diff.patch"

# ----------------------------------------------------------------------------
# Secret Scan (Pre-flight)
# ----------------------------------------------------------------------------

log "Scanning diff for secrets..."
# Simple regex for common keys. 
if grep -qE "API_KEY|password|secret|token|AWS_ACCESS_KEY|PRIVATE_KEY" "$OUTPUT_DIR/diff.patch"; then
    echo "================================================================"
    echo "🚨 [WARN] POTENTIAL SECRETS DETECTED IN DIFF 🚨"
    echo "   Patterns matched: API_KEY/password/secret/token/AWS..."
    echo "   Please review $OUTPUT_DIR/diff.patch carefully."
    echo "================================================================"
    
    if [[ "$DRY_RUN" != "true" ]]; then
         read -p "Are you sure you want to send this to the LLM? [y/N] " -n 1 -r
         echo
         if [[ ! $REPLY =~ ^[Yy]$ ]]; then
             error "Aborted by user due to secret warning."
         fi
    fi
else
    log "No obvious secrets found (Basic Regex Scan)."
fi

# ----------------------------------------------------------------------------
# Prompt Rendering
# ----------------------------------------------------------------------------

RENDERED_PROMPT="$OUTPUT_DIR/prompt.txt"
export BUNDLE_PATH="$(realpath "$OUTPUT_DIR")"

# Fetch Context
CONTEXT_FILE="$OUTPUT_DIR/context.json"
log "Fetching context for repo: $REPO_NAME"
"$PYTHON_CMD" scripts/db_manager.py get-context "$REPO_NAME" 3 > "$CONTEXT_FILE"

log "Rendering prompt template: $WF_PROMPT"
if ! "$PYTHON_CMD" scripts/render_prompt.py "$WF_PROMPT" "$OUTPUT_DIR/diff.patch" "$REPO_NAME" "$CONTEXT_FILE" > "$RENDERED_PROMPT"; then
    error "Failed to render prompt"
fi

# ----------------------------------------------------------------------------
# Token Guard / Pruning
# ----------------------------------------------------------------------------

if [[ "$WF_LLM" == "gemini" ]]; then
    TOKEN_LIMIT=$(get_config "$SETUP_FILE" ".get('token_limit', 1000000)")
    
    export GEMINI_MODEL="$WF_MODEL"
    # Capture output, ignore errors (fallback to no pruning)
    COUNT_OUTPUT=$("$PYTHON_CMD" scripts/call_gemini.py --count-tokens "$RENDERED_PROMPT" 2>/dev/null || echo "Error")
    
    if [[ "$COUNT_OUTPUT" == *"Estimated Tokens:"* ]]; then
        TOKEN_COUNT=$(echo "$COUNT_OUTPUT" | grep "Estimated Tokens:" | awk '{print $3}')
        log "Token Count: $TOKEN_COUNT (Limit: $TOKEN_LIMIT)"
        
        if [[ "$TOKEN_COUNT" -gt "$TOKEN_LIMIT" ]]; then
            log "⚠️  Token count exceeds limit! Pruning context (switching to --stat)..."
            
            # Pruning: Use --stat
            # We need to regenerate diff content
            # TARGET_REF and SOURCE_REF are already set above
            DIFF_CONTENT=$(git -C "$REPO_PATH" diff --stat "$TARGET_REF...$SOURCE_REF")
            
            if [[ -z "$DIFF_CONTENT" ]]; then
                 log "Pruned diff is empty? Keeping original."
            else
                echo "$DIFF_CONTENT" > "$OUTPUT_DIR/diff.patch"
                
                # Re-render
                if ! "$PYTHON_CMD" scripts/render_prompt.py "$WF_PROMPT" "$OUTPUT_DIR/diff.patch" "$REPO_NAME" "$CONTEXT_FILE" > "$RENDERED_PROMPT"; then
                    error "Failed to re-render prompt after pruning"
                fi
                log "Pruned prompt rendered."
            fi
        fi
    else
        log "[WARN] Could not estimate tokens. Skipping guard."
    fi
fi

# ----------------------------------------------------------------------------
# Cache Check
# ----------------------------------------------------------------------------

RESULT_FILE="$OUTPUT_DIR/llm_result.md"
CACHE_HIT="false"

# Generate Base Prompt for Hashing (Context-Free)
# This ensures that growing context history doesn't invalidate the cache for the same diff/template.
BASE_PROMPT_FILE="$OUTPUT_DIR/prompt_base.txt"
if ! "$PYTHON_CMD" scripts/render_prompt.py "$WF_PROMPT" "$OUTPUT_DIR/diff.patch" "$REPO_NAME" > "$BASE_PROMPT_FILE"; then
    log "[WARN] Failed to render base prompt for hashing. Using full prompt hash."
    BASE_PROMPT_FILE="$RENDERED_PROMPT"
fi

# Calculate Hashes
if command -v sha256sum &>/dev/null; then
    DIFF_HASH=$(sha256sum "$OUTPUT_DIR/diff.patch" | awk '{print $1}')
    PROMPT_HASH=$(sha256sum "$BASE_PROMPT_FILE" | awk '{print $1}')
else
    # Fallback for systems without sha256sum (e.g. some macs use shasum -a 256)
    DIFF_HASH=$(shasum -a 256 "$OUTPUT_DIR/diff.patch" | awk '{print $1}')
    PROMPT_HASH=$(shasum -a 256 "$BASE_PROMPT_FILE" | awk '{print $1}')
fi

if [[ "$DRY_RUN" != "true" ]]; then
    log "Checking cache for DiffHash=${DIFF_HASH:0:8} PromptHash=${PROMPT_HASH:0:8} Model=$WF_MODEL..."
    if "$PYTHON_CMD" scripts/db_manager.py get "$DIFF_HASH" "$PROMPT_HASH" "$WF_MODEL" > "$RESULT_FILE"; then
        log "Cache HIT! Using cached response."
        CACHE_HIT="true"
    else
        log "Cache MISS."
    fi
fi

# ----------------------------------------------------------------------------
# Dry Run / Token Count
# ----------------------------------------------------------------------------

if [[ "$DRY_RUN" == "true" ]]; then
    log "Dry Run Mode: Skipping API call."
    
    if [[ "$WF_LLM" == "gemini" ]]; then
         log "Estimating token count (Gemini SDK)..."
         export GEMINI_MODEL="$WF_MODEL"
         "$PYTHON_CMD" scripts/call_gemini.py --count-tokens "$RENDERED_PROMPT" || log "Token counting failed (API key valid?)"
    fi

    echo ""
    echo "=============================================================================="
    echo "✅ Dry Run Completed"
    echo "=============================================================================="
    echo "📂 Artifacts: $OUTPUT_DIR"
    echo "📄 Prompt:    $RENDERED_PROMPT"
    echo ""
    echo "👉 NEXT STEPS (To run for real):"
    echo "   Run the command again without the --dry-run flag:"
    echo "   $0 --repo $REPO_NAME --workflow $WORKFLOW"
    echo "=============================================================================="
    exit 0
fi

# ----------------------------------------------------------------------------
# LLM Invocation
# ----------------------------------------------------------------------------

if [[ "$WF_LLM" == "gemini" ]]; then
    if [[ "$CACHE_HIT" == "false" ]]; then
        log "Calling Gemini API ($WF_MODEL)..."
        export GEMINI_MODEL="$WF_MODEL"
        if ! "$PYTHON_CMD" scripts/call_gemini.py "$RENDERED_PROMPT" "$RESULT_FILE"; then
            error "Gemini API call failed"
        fi
        log "Result saved to $RESULT_FILE"

        # Save to Cache
        log "Saving result to cache..."
        "$PYTHON_CMD" scripts/db_manager.py save "$DIFF_HASH" "$PROMPT_HASH" "$WF_MODEL" "$RESULT_FILE" "0.0" "$REPO_NAME"
    fi
    
    # Validate output if JSON format requested or explicitly strictly structured
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        log "Validating JSON output..."
        if ! "$PYTHON_CMD" scripts/validate_output.py "$RESULT_FILE"; then
             log "[WARN] JSON validation failed."
        fi
    elif [[ "$WORKFLOW" == "data_extraction" ]]; then
        log "Validating Structured output..."
         if ! "$PYTHON_CMD" scripts/validate_output.py "$RESULT_FILE"; then
             log "[WARN] validation failed."
        fi
    fi
    
elif [[ "$WF_LLM" == "copilot" ]]; then
    log "Copilot workflow: Prompt saved to $RENDERED_PROMPT"
    COPIED_TO_CLIPBOARD="false"
    if command -v wl-copy &>/dev/null; then
        cat "$RENDERED_PROMPT" | wl-copy
        log "Prompt copied to clipboard (Wayland)"
        COPIED_TO_CLIPBOARD="true"
    elif command -v xclip &>/dev/null; then
        cat "$RENDERED_PROMPT" | xclip -selection clipboard
        log "Prompt copied to clipboard (X11)"
        COPIED_TO_CLIPBOARD="true"
    elif command -v pbcopy &>/dev/null; then
        cat "$RENDERED_PROMPT" | pbcopy
        log "Prompt copied to clipboard (macOS)"
        COPIED_TO_CLIPBOARD="true"
    else
        log "Please copy content of $RENDERED_PROMPT to Copilot"
    fi
else
    error "Unknown LLM provider: $WF_LLM"
fi

# ----------------------------------------------------------------------------
# Post Steps
# ----------------------------------------------------------------------------

if [[ -n "$POST_STEPS" && "$POST_STEPS" != "None" ]]; then
    log "Executing post_steps: $POST_STEPS"
    
    if ! "$PYTHON_CMD" -c "import prefect" 2>/dev/null; then
        error "Workflow requires 'prefect' for post_steps, but it is not installed."
    fi
    
    FLOW_FILE="${POST_STEPS%%:*}"
    FLOW_FUNC="${POST_STEPS#*:}"
    FULL_FLOW_PATH="$REPO_PATH/$FLOW_FILE"
    
    if [[ ! -f "$FULL_FLOW_PATH" ]]; then
        error "Post steps flow file not found: $FULL_FLOW_PATH"
    fi
    
    python3 << EOF
import sys
sys.path.insert(0, "$REPO_PATH")
from importlib import import_module
from pathlib import Path

flow_path = Path("$FLOW_FILE").with_suffix("")
module_path = str(flow_path).replace("/", ".")
module = import_module(module_path)
flow_func = getattr(module, "$FLOW_FUNC")
result = flow_func(output_dir="$OUTPUT_DIR", repo_name="$REPO_NAME")
print(f"[INFO] Post steps result: {result}")
EOF

    if [[ $? -ne 0 ]]; then
        error "Post steps execution failed"
    fi
    log "Post steps completed."
fi

# ----------------------------------------------------------------------------
# Final Summary / Next Steps
# ----------------------------------------------------------------------------

echo ""
echo "=============================================================================="
echo "✅ Workflow Completed Successfully"
echo "=============================================================================="
echo "📂 Artifacts: $OUTPUT_DIR"

if [[ "$WF_LLM" == "copilot" ]]; then
    echo "🤖 Mode:      Copilot (Manual)"
    echo "📄 Prompt:    $RENDERED_PROMPT"
    echo ""
    echo "👉 NEXT STEPS:"
    if [[ "$COPIED_TO_CLIPBOARD" == "true" ]]; then
        echo "   1. The prompt has been COPIED to your clipboard."
        echo "   2. Open GitHub Copilot Chat (or your preferred agent)."
        echo "   3. Paste (Ctrl+V / Cmd+V) and hit Enter."
    else
        echo "   1. Open $RENDERED_PROMPT"
        echo "   2. Copy the entire content."
        echo "   3. Paste it into GitHub Copilot Chat (or your preferred agent)."
    fi
elif [[ "$WF_LLM" == "gemini" ]]; then
    echo "🤖 Mode:      Gemini (Automated)"
    echo "📄 Result:    $RESULT_FILE"
    echo ""
    echo "👉 NEXT STEPS:"
    echo "   1. Review the generated analysis in $RESULT_FILE"
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        echo "   2. Process the JSON output as needed."
    fi
fi
echo "=============================================================================="


