# Human approval flow

```
agent proposes call
      |
 gate verdict = require_approval
      |
 request persisted -> .acp/approvals.json   (id, tool, case, args hash, reason)
      |
 human decides OUT OF BAND                  agent does NOT execute
   - CLI:      acp approvals list / approve <id> / deny <id>
   - Phone:    any client that can read the queue and flip a decision --
               a fold-phone dashboard, a Telegram/WhatsApp bot, a push
               notification with Approve/Deny actions
   - Webhook stub: POST /approvals/{id}/decision {"approved": true}
               (implement in ~20 lines with your framework of choice;
               the queue file / table is the entire contract)
      |
 decision recorded in the queue + every gate verdict in audit.jsonl
```

Notes:
- Approvals are **per call** (tool + args hash + case), never blanket
  "approve this tool forever". A changed argument is a new request.
- Denied-by-human is terminal for that call; the agent must replan, which
  the dedupe store also enforces for identical retries.
- In an enterprise deployment this maps to your existing approval surface
  (Teams/Slack workflow, ServiceNow, a Databricks App) — see
  `docs/databricks-mapping.md`.
