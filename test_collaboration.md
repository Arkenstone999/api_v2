# Testing Agent Collaboration

## Quick Test

```bash
# Start the API
uv run uvicorn crewsastosparksql.api.app:app --host 0.0.0.0 --port 8000

# In another terminal, submit a SAS file
curl -X POST http://localhost:8000/jobs \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@your_file.sas"

# Watch logs for collaboration
```

## What to Look For

### Delegation Signals

When agents collaborate, you'll see:

```
INFO: Agent platform_architect needs clarification
INFO: Delegating to agent sas_analyst
INFO: Agent sas_analyst providing response
INFO: Agent platform_architect resuming with new context
```

### Context Sharing

```
INFO: Task 'translate_code' has access to 2 context tasks
INFO: Reading output from: analyze_sas
INFO: Reading output from: decide_platform
```

### Natural Questions

Agents will ask each other:

**platform_architect → sas_analyst:**
> "The complexity score is borderline. Does this code have heavy data aggregations or just simple filters?"

**code_translator → platform_architect:**
> "The implementation guidance mentions window functions. Should I use PARTITION BY or GROUP BY for this aggregation?"

**test_engineer → sas_analyst:**
> "What's the typical cardinality of the customer_id column for realistic test data?"

**code_reviewer → code_translator:**
> "The error handling is missing for null values. Please add proper null checks."

## Collaboration Scenarios

### Scenario 1: Ambiguous Complexity

1. **sas_analyst** analyzes code, flags complexity as borderline (score: 5)
2. **platform_architect** sees flag, delegates back to ask about data volumes
3. **sas_analyst** provides estimate: "Typically 100k rows"
4. **platform_architect** decides: SQL (data size doesn't require PySpark)

### Scenario 2: Implementation Clarification

1. **code_translator** reads architect's guidance: "Use CTEs for modularity"
2. Translator encounters complex nested logic
3. Delegates to **platform_architect**: "Should I split this into 3 CTEs or 2?"
4. **platform_architect** responds: "Use 3 CTEs - one per logical grouping"

### Scenario 3: Test Data Patterns

1. **test_engineer** needs to generate realistic test data
2. Analysis doesn't specify value ranges for `amount` column
3. Delegates to **sas_analyst**: "What's typical range for amount?"
4. **sas_analyst** responds: "0-10000, mean around 500"

### Scenario 4: Code Review Fixes

1. **code_reviewer** finds bug: missing null handling
2. Delegates to **code_translator**: "Add null checks for customer_id"
3. **code_translator** updates code and writes new version
4. **code_reviewer** validates fix and approves

## Benefits You'll See

### Fewer Errors
Agents clarify ambiguities before proceeding

### Better Quality
Collaboration catches issues early

### Realistic Code
Test data matches actual patterns

### Faster Iteration
Review feedback immediately triggers fixes

## Configuration for Maximum Collaboration

```yaml
# agents.yaml
all_agents:
  allow_delegation: true  # Enable collaboration
  verbose: true           # See delegation in logs

code_reviewer:
  allow_delegation: true  # CRITICAL - can delegate fixes back
```

```python
# crew.py
process=Process.sequential  # Agents execute in order, can still delegate
verbose=True                # Log all delegation
```

## Monitoring Collaboration

### Logs
```bash
tail -f logs/crew.log | grep -i "delegat"
```

### Metrics
- Count delegations per job
- Track which agent pairs collaborate most
- Measure impact on output quality

## Success Indicators

Collaboration is working when you see:
- ✅ Agents asking questions mid-task
- ✅ Context-aware responses
- ✅ Fixes applied based on feedback
- ✅ No "placeholder" messages
- ✅ Natural conversation in logs

## Common Questions

**Q: How many times will agents delegate?**
A: As needed. CrewAI prevents infinite loops.

**Q: Can any agent ask any other agent?**
A: Yes, if `allow_delegation: true`. CrewAI routes intelligently.

**Q: Do I need to explicitly tell agents when to delegate?**
A: No. They delegate naturally when they need help.

**Q: What if an agent delegates to the wrong specialist?**
A: CrewAI uses agent roles/goals to route correctly. Improve agent descriptions if needed.

## Result

Real collaboration. Agents work as a team. Production ready.
