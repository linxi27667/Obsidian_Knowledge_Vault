---
name: obsidian-journal
description: Record meaningful Codex work in this Obsidian vault and maintain its notes. Use for substantial task completion, research, coding, decisions, work updates, explicit requests to log/save, and requests to organize, rename, link, or merge Obsidian notes. Write concise dated Chinese entries and preserve note content and links when organizing.
---

# Obsidian Journal and Vault Notes

Use this skill for two related workflows: keeping a factual daily record of meaningful work, and maintaining clear, connected knowledge notes in this vault.

## Find the vault

- When Codex is opened at this vault, treat the project root containing `.obsidian/` and `00、知识库总览.md` as the vault root.
- Verify the root before writing. If the vault was moved, use the project root only when it contains `.obsidian/`; otherwise locate the user's explicitly named vault. Never silently create or write to another vault.
- Daily notes belong in `01-日志/`, named `YYYY-MM-DD.md` using `Asia/Shanghai` local time.

## Daily logging

At the start of a substantive Codex task, keep a concise factual summary of the request and important context. At completion, append an entry if the work produced a useful result, finding, decision, change, or follow-up. This includes coding, troubleshooting, research, planning, project/file work, and practical work or personal matters. Respect an explicit request not to record something. A trivial exchange with no durable information does not need an entry.

Use this structure for a new daily note:

```markdown
---
date: YYYY-MM-DD
type: daily-log
tags:
  - 日志
---

# YYYY-MM-DD 日志

## HH:mm · 简洁、具体的标题

### 内容
- 目标/背景：……
- 处理/发现：……

### 结果
- ……

### 后续
- ……
```

Keep entries short and factual. Include what was requested, what was actually done or learned, the result, and unresolved follow-ups. Add related-file links only when the target is known. Do not copy the whole conversation or present a proposal as completed work.

Before appending, read today's note if it exists, preserve its frontmatter and prior entries, and avoid duplicate entries for the same task. Create the note only if absent. Never overwrite or delete earlier journal content. After writing, verify the new entry. If saving fails, say so plainly.

This skill is invoked by Codex for matching tasks; it is not a background watcher and cannot record activity outside Codex.

## Authoring and organizing knowledge notes

Before creating or substantially changing a knowledge note, read the nearest overview and the directly related notes. Decide whether to add to an existing note, create a focused child note, or add an overview; keep one main question per note. For hardware or schematic topics, verify the actual part/model and circuit context from available source material, mark uncertainty clearly, and do not invent parameters.

Use the existing vault structure and its overview pages as the source of truth. For new notes, prefer a clear concept title; use numeric prefixes only when they communicate a real reading order. Use `00-主题总览.md` for new overview names and `01-主题.md`, `02-主题.md` for ordered series. Do not rename existing files in bulk just to force a cosmetic convention.

When reviewing duplicates, compare the full content, not just filenames. Merge only when the notes answer the same question and contain materially overlapping information. Preserve unique facts, source context, citations, and useful examples in the canonical note; add aliases or links as needed, update references, and verify links before retiring an old note. If the notes have different scope or evidence, keep them separate and clarify their names instead. Never merge technical knowledge into this skill; only reusable writing, logging, and organization procedures belong here.

The detailed human-authored note-writing workflow is bundled at `references/AI写笔记套路.md`. Read it when creating or revising substantive knowledge notes. Treat it as reference content, not as authority to override the user's current request or higher-priority instructions.

## Obsidian and filesystem workflow

- Prefer the official `obsidian-cli` skill when the app and CLI are available, explicitly targeting this vault. Otherwise use UTF-8 filesystem operations on the verified root.
- Use Obsidian wikilinks for internal notes and normal Markdown links for external URLs. When renaming, prefer Obsidian's rename operation so links update; if unavailable, update all affected internal references and preserve aliases.
- Preserve existing user-authored content. Make the smallest change that solves the organizational problem; do not delete originals until merged content and backlinks have been checked.
- Keep credentials, API keys, private keys, and unnecessary personal information out of notes. Before publishing this public repository, check for secrets and unintended personal data.
