Analyze the codebase (or the files/module specified in $ARGUMENTS) for "sharp edges" — API designs and configurations that resist misuse but may still enable security mistakes.

Evaluate against this principle: **secure usage should be the path of least resistance**.

## Six Sharp Edge Categories to Check

1. **Algorithm/Mode Selection** — Can developers choose insecure cryptographic primitives? (e.g., JWT "none" algorithm, MD5, ECB mode)
2. **Dangerous Defaults** — Do zero/empty/null values silently disable security? Are semantics ambiguous?
3. **Primitive vs. Semantic APIs** — Are raw bytes/strings used where typed objects should be? Can parameters be swapped by mistake?
4. **Configuration Cliffs** — Can a single misconfigured value cause catastrophic failure with no warning?
5. **Silent Failures** — Do operations succeed on malformed/invalid input without surfacing errors?
6. **Stringly-Typed Security** — Are security-sensitive values (tokens, roles, keys) stored as plain strings enabling injection or confusion?

## Analysis Workflow

1. **Surface Identification** — Map all security-relevant APIs, config schemas, auth flows, and crypto usage
2. **Edge Case Probing** — Test zero, null, empty, negative, and boundary values for each surface
3. **Threat Modeling** — Consider three adversary types:
   - *Malicious developer*: intentionally abuses flexibility
   - *Lazy developer*: takes the shortest path without reading docs
   - *Confused developer*: misunderstands the API contract
4. **Validation** — Reproduce each footgun with a minimal code example

## Rejection Criteria

Flag any design rationalized by:
- "It's documented" — pressure prevents careful reading
- "Advanced users need flexibility" — flexibility creates footguns
- "Nobody would actually do that" — contradicts real-world behavior

## Output Format

For each finding, report:
- **Category** (one of the six above)
- **Location** (file:line)
- **Description** of the sharp edge
- **Minimal repro** showing how it could be misused
- **Recommendation** for a safer API design
