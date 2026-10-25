# Demo data
The demo agent's `file_lookup` tool searches a tiny built-in corpus in
`tools.py` (handbook / travel / on-call notes) so the project runs offline
with zero setup. Point it at a real folder or vector store in production --
the gate does not care what the tool does, only whether the call may run.
