"""
Python implementation of CLAUDE.md's "Robinhood Automated Trading Agent Guardrails".

This package is a faithful, ordered translation of the markdown spec in CLAUDE.md (root of
this repo) into runnable code: same parameters, same seven-step execution sequence, same
gates/guards. See bot/README.md for what's a direct translation vs. what you still need to
wire up (broker credentials, tax-lot/realized-P&L endpoints, Gmail/GitHub auth).

Entry point: `python -m bot.main --account <acct> [--live]`
"""
