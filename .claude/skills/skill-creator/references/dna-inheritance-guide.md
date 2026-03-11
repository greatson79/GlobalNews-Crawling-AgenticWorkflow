# DNA Inheritance Guide for Skills

Every skill born from AgenticWorkflow must structurally embed the parent genome.
This guide maps genome genes to their concrete expression in skills.

## Mandatory Genes (must appear in every skill)

### Gene 1: Quality Absolutism
**Source**: soul.md §0, CLAUDE.md Absolute Rule 1
**Expression**: `## Absolute Rules` section with explicit quality-over-speed statement

Example:
```markdown
## Absolute Rules
1. **Quality over speed** — The only criterion is output quality. Ignore token cost, time, and volume constraints.
```

### Gene 2: SOT Pattern
**Source**: CLAUDE.md Absolute Rule 2
**Expression**: If the skill manages state, it must use single-file SOT. If not, acknowledge read-only access.

Example (state-managing skill):
```markdown
2. **Single SOT** — All shared state in one file. Distributed state is forbidden.
```

Example (read-only skill):
```markdown
2. **SOT Read-Only** — Read state.yaml for context. Never write directly.
```

### Gene 3: English-First Execution
**Source**: CLAUDE.md Language Rules
**Expression**: Working language rule in `## Absolute Rules` or dedicated `## Language Rule` section

Example:
```markdown
3. **English-First** — Agents work in English. Translation delegated to @translator.
```

## Recommended Genes (include when applicable)

### Gene 4: 4-Layer Quality Assurance
**When**: Skill produces outputs that need verification
**Expression**: Verification criteria + pACS self-rating protocol

### Gene 5: P1 Hallucination Prevention
**When**: Skill has tasks requiring 100% accuracy repeatedly
**Expression**: `## P1 Targets` section identifying Python-enforced validations

### Gene 6: Safety Hooks
**When**: Skill involves potentially destructive operations
**Expression**: PreToolUse guards or validation scripts

### Gene 7: RLM Pattern
**When**: Skill works with large context that should stay external
**Expression**: File pointers instead of full content injection

## Minimum Requirement

A valid skill must express **at least 3 genes** from the table above.
Quality Absolutism (Gene 1) and English-First (Gene 3) are always required.
The third gene depends on the skill's domain.

## Validation Checklist

- [ ] Gene 1 (Quality Absolutism): Present in Absolute Rules
- [ ] Gene 3 (English-First): Present in Absolute Rules or Language Rule
- [ ] Third gene: Identified and expressed
- [ ] No gene contradicts another (e.g., quality rule doesn't conflict with SOT rule)
- [ ] Gene expressions are domain-specific, not copy-pasted boilerplate
