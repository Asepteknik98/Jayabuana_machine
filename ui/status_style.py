"""Shared presentation colors and unit formatting; no decision logic."""
COLORS = {"SAFE":"#4cde9a", "NORMAL":"#4cde9a", "VALID":"#4cde9a", "ACTIVE":"#4cde9a",
    "CAUTION":"#efc34a", "WARN":"#efc34a", "STALE":"#efc34a", "VERIFY":"#efc34a",
    "HIGH":"#ff8c42", "SLOW":"#ff8c42", "DEGRADED":"#ff8c42",
    "CRITICAL":"#ff5353", "RESTRICT":"#ff5353", "UNKNOWN":"#94aec3", "OFFLINE":"#94aec3"}

def metres(value):
    return "N/A" if value is None else f"{value:.2f} m"

def percent(value):
    return "N/A" if value is None else f"{value:.0%}"
