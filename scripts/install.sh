#!/usr/bin/env bash
# install.sh —— 把本 skill 安装到各 agent 的 skills 目录（跨 agent 兼容）
#
# 用法：
#   bash scripts/install.sh            # 默认 symlink（推荐：单一事实源，更新即生效）
#   bash scripts/install.sh --copy     # 复制（各 agent 独立副本，需手动同步更新）
#
# 说明：SKILL.md 格式遵循开放规范（agentskills.io），各 agent 均可识别；
#       差异仅在发现路径。未安装的 agent（目录不存在）自动跳过。
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_NAME="$(basename "$SKILL_DIR")"
MODE="${1:---link}"
TARGETS=(
  "$HOME/.agents/skills"      # ZCode 等遵循开放规范的 agent
  "$HOME/.claude/skills"      # Claude Code
  "$HOME/.codex/skills"       # Codex CLI
  "$HOME/.gemini/skills"      # Gemini CLI
  "$HOME/.openclaw/skills"    # OpenClaw
)
for t in "${TARGETS[@]}"; do
  # agent 未安装则跳过
  if [ ! -d "$(dirname "$t")" ]; then
    echo "跳过（未检测到）: $t"
    continue
  fi
  # 防自链接：skill 已在本目录内时跳过
  if [ "$(cd "$t" 2>/dev/null && pwd)" = "$(cd "$SKILL_DIR/.." && pwd)" ]; then
    echo "跳过（已在此目录）: $t"
    continue
  fi
  mkdir -p "$t"
  dest="$t/$SKILL_NAME"
  rm -rf "$dest"
  if [ "$MODE" = "--copy" ]; then
    cp -R "$SKILL_DIR" "$dest"
    echo "复制 → $dest"
  else
    ln -s "$SKILL_DIR" "$dest"
    echo "链接 → $dest"
  fi
done
echo "完成（模式 ${MODE}）。各 agent 新会话生效。"
