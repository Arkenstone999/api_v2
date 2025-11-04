# Agent Collaboration Guide

## What Changed

**Before:** Placeholder `call_agent` tool that didn't work
**After:** Real CrewAI delegation with `allow_delegation: true`

## How Collaboration Works Now

### Native CrewAI Delegation

When `allow_delegation: true`, agents can automatically delegate to each other:

```yaml
platform_architect:
  allow_delegation: true  # Can now ask sas_analyst for clarifications
```

Agents will naturally delegate when they:
- Need clarification on previous work
- Encounter ambiguous requirements
- Need expertise from another specialist

### Example Collaboration Flow

1. **platform_architect** reads analysis, finds ambiguity
2. CrewAI automatically routes question to **sas_analyst**
3. **sas_analyst** provides clarification
4. **platform_architect** continues with decision

No tool calls needed - it's natural conversation between agents.

### Task Context

Tasks use `context` to share outputs:

```yaml
translate_code:
  context: [analyze_sas, decide_platform]  # Has access to both outputs
```

This means:
- **code_translator** sees analysis AND platform decision
- **code_reviewer** sees ALL previous work
- Agents build on each other's work

## Benefits

### Simple
- No placeholder tools
- No manual "call_agent()" syntax
- Agents just ask questions naturally

### Collaborative
- **platform_architect** can ask **sas_analyst** about SAS specifics
- **code_translator** can ask **platform_architect** about implementation approach
- **test_engineer** can ask **sas_analyst** about data patterns
- **code_reviewer** can delegate fixes back to **code_translator**

### Production Ready
- Uses CrewAI's built-in delegation system
- Tested and reliable
- Scales with crew size

## Configuration

### Enable Delegation

```yaml
agent_name:
  allow_delegation: true  # Enable collaboration
```

### Backstory Hints

Update backstories to mention collaboration:

```yaml
backstory: "Can ask the SAS analyst for clarifications when needed."
```

This guides the LLM to use delegation naturally.

## Testing Collaboration

Run a job and watch for delegation:

```bash
uv run python run_api.py
```

Look for logs like:
```
INFO: Agent 'platform_architect' delegating to 'sas_analyst'
INFO: Agent 'sas_analyst' responding to delegation request
```

## When Agents Delegate

Agents delegate when they:
1. **Need context** - "What does this SAS macro do?"
2. **Hit ambiguity** - "Is this value always positive?"
3. **Want validation** - "Does this approach make sense?"
4. **Request fixes** - "Please improve error handling"

## Best Practices

### 1. Clear Roles
Each agent has distinct expertise:
- **sas_analyst** - SAS code knowledge
- **platform_architect** - Platform decisions
- **code_translator** - Code generation
- **test_engineer** - Testing
- **code_reviewer** - Quality validation

### 2. Sequential Process
```python
process=Process.sequential
```

Ensures agents execute in order, building on previous work.

### 3. Task Context
Always specify which prior tasks an agent needs:

```yaml
review_and_approve:
  context: [analyze_sas, decide_platform, translate_code, test_and_validate]
```

### 4. Verbose Logging
```yaml
verbose: true  # See delegation happening
```

## Comparison

### Old Way (Placeholder)
```python
# Doesn't actually work
call_agent(agent_name='sas_analyst', question='...')
# Returns: "[REQUEST TO SAS_ANALYST]: ..."
```

### New Way (Real Delegation)
```python
# Happens automatically when agent needs help
# CrewAI routes to appropriate agent
# Returns actual response from delegated agent
```

## Technical Details

CrewAI delegation uses:
- LLM function calling to detect delegation intent
- Crew routing to find target agent
- Context passing for seamless handoff
- Result aggregation back to requesting agent

All handled automatically - just set `allow_delegation: true`.

## Troubleshooting

### Agent Not Delegating?
- Check `allow_delegation: true` in agents.yaml
- Verify backstory mentions collaboration capability
- Ensure task context includes relevant prior tasks

### Too Much Delegation?
- Add more detail to task descriptions
- Provide clearer guidance in expected_output
- Consider if agent needs more tools (file_reader, etc)

### Delegation Loop?
- Review agent roles for overlap
- Ensure clear handoff points in tasks
- Check that context dependencies are correct

## Result

Simple, functional collaboration. No overengineering. Agents work together naturally.
