# Tool Selection Guide for Sub-Agents

Principle: **Minimum privilege, maximum capability**. Grant only needed tools, but never withhold a tool that improves output quality (Absolute Rule 1 overrides minimalism).

## Tool Catalog

| Tool | Capability | Typical Agents |
|------|-----------|----------------|
| **Read** | Read files (code, docs, configs, images, PDFs) | Nearly all agents |
| **Write** | Create new files | Agents producing outputs |
| **Edit** | Modify existing files (surgical edits) | Code modification agents |
| **Bash** | Execute shell commands, run tests | Build/test/infrastructure agents |
| **Glob** | Find files by name pattern | Codebase exploration agents |
| **Grep** | Search file contents by regex | Analysis/review agents |
| **WebFetch** | Fetch content from URLs | Data collection agents |
| **WebSearch** | Search the web | Research agents |

## Role-Based Presets

### Research Agent
```yaml
tools: Read, Glob, Grep, WebFetch, WebSearch
```
Reads existing code/docs, searches codebase, fetches external sources. No write access needed.

### Code Developer
```yaml
tools: Read, Write, Edit, Bash, Glob, Grep
```
Full local development capability. No web access unless researching external APIs.

### Reviewer / Fact-Checker (Read-Only)
```yaml
tools: Read, Glob, Grep
```
Adversarial review agents must be read-only to prevent self-modification of reviewed outputs.
Add `WebFetch, WebSearch` for fact-checkers that need external verification.

### Translator
```yaml
tools: Read, Write, Glob, Grep
```
Reads source documents, writes translations, searches for glossary/terminology.

### Infrastructure / DevOps
```yaml
tools: Read, Write, Edit, Bash, Glob, Grep
```
Full file and shell access for configuration, scripting, automation.

### Data Analyst
```yaml
tools: Read, Write, Bash, Glob, Grep
```
Processes data files, runs analysis scripts, writes output reports.

## Decision Matrix

Answer these questions to determine the tool set:

1. **Does the agent produce file outputs?**
   - Yes → Add `Write`
   - Modifies existing files → Add `Edit`

2. **Does the agent run commands (tests, builds, scripts)?**
   - Yes → Add `Bash`

3. **Does the agent search the codebase?**
   - By filename → Add `Glob`
   - By content → Add `Grep`
   - Both → Add both

4. **Does the agent need external data?**
   - Specific URLs → Add `WebFetch`
   - Open-ended research → Add `WebFetch, WebSearch`

5. **Is the agent adversarial (reviewer, verifier)?**
   - Yes → Remove `Write, Edit` (read-only enforcement)
   - Exception: fact-checkers may need `WebFetch, WebSearch`

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Giving all tools to every agent | Violates minimum privilege, increases risk | Use role-based presets |
| Withholding `Bash` from code agents | Can't run tests → quality drops | Grant `Bash` if testing is part of verification |
| Giving `Write` to reviewers | Reviewer can modify what they review | Reviewers must be read-only |
| No `Grep` for analysis agents | Agent can't search efficiently → wastes turns | Always grant `Grep` for analysis roles |
