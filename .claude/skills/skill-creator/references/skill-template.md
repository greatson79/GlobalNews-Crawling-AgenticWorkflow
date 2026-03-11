# Skill Template

Use this template as a starting point for new skills. Replace all `[bracketed]` values.

```markdown
---
name: [skill-name]
description: [1-2 sentence description. Include trigger patterns like "use when user requests X, Y, or Z".]
---

# [Skill Display Name]

[1-sentence purpose statement.]

## Absolute Rules

1. **Quality over speed** — [domain-specific quality statement]. Token cost and time are irrelevant.
2. **[Domain DNA Rule]** — [Inherited pattern from AgenticWorkflow genome].
3. **English-First Execution** — All working outputs in English. Korean translation via @translator.

## Prerequisites

[What must be true before this skill executes:]

1. [Required file/data/state]
2. [Required tool/capability]
3. [Required context]

## Protocol

### Step 1: Context Loading

[What to read before starting. Reference existing outputs, SOT state, specs.]

### Step 2: [Core Work Phase Name]

[Main execution steps. Be specific about inputs, processing, and expected outputs.]

### Step 3: Self-Verification

Verify output against these criteria before completing:

- [ ] [Criterion 1 — measurable, deterministic]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

### Step 4: Output Generation

[Where to write output, expected format, naming convention.]

## P1 Targets

Tasks requiring 100% accuracy — implement as Python scripts, not LLM judgment:

| Task | Script | Validation |
|------|--------|-----------|
| [e.g., File existence check] | [e.g., validate_X.py] | [e.g., X1-X3 checks] |

## Quality Checklist

- [ ] Output file exists and is non-empty
- [ ] All verification criteria met
- [ ] DNA genes injected (minimum 3)
- [ ] P1 targets identified and scripted
- [ ] English-First rule followed

## Anti-Patterns

- [Pattern to avoid] → [Why it's wrong] → [What to do instead]
```

## Key Guidelines

1. **frontmatter is mandatory**: `name` (kebab-case) and `description` (with trigger patterns) are required
2. **Absolute Rules derive from parent**: Always include Quality Absolutism + at least 2 domain-specific DNA rules
3. **Protocol must be sequential**: Each step builds on the previous — no ambiguous parallel steps
4. **P1 targets must be explicit**: If a task repeats and must be 100% correct, it gets a Python script
5. **references/ is optional**: Only create files that provide concrete value (templates, examples, checklists)
