"""Model Context Protocol (MCP) server for NetEyes.

Allows any MCP-compliant client (Claude Desktop, Cursor, Windsurf, Zed, OpenClaw)
to use NetEyes capabilities directly over standard JSON-RPC stdin/stdout transport.
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, Dict, List, Optional

from neteyes import __version__
from neteyes.channels import list_channels, normalize_channel_id
from neteyes.doctor import run_doctor
from neteyes.router import run as run_action


MCP_PROTOCOL_VERSION = "2024-11-05"


def get_mcp_tools() -> List[Dict[str, Any]]:
    """Return list of tool specifications conforming to MCP schema."""
    tools: List[Dict[str, Any]] = [
        {
            "name": "neteyes_doctor",
            "description": "Probe health, available CLI binaries, packages, and active backends for all internet channels.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "include_fix_prescriptions": {
                        "type": "boolean",
                        "description": "Whether to return actionable fix prescriptions for degraded backends",
                        "default": True,
                    }
                },
            },
        }
    ]

    channels = list_channels()
    for ch in channels:
        for action in ch.actions:
            tool_name = f"neteyes_{ch.id}_{action.name}"
            properties = {}
            for param, desc in action.parameters.items():
                properties[param] = {
                    "type": "string",
                    "description": desc,
                }
            tools.append({
                "name": tool_name,
                "description": f"[{ch.name}] {action.description}",
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": list(action.parameters.keys()),
                },
            })

    return tools


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call and format the result for MCP."""
    if name == "neteyes_doctor":
        report = run_doctor()
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(report.model_dump(), indent=2, ensure_ascii=False),
                }
            ],
            "isError": False,
        }

    if not name.startswith("neteyes_"):
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            "isError": True,
        }

    parts = name.split("_")
    # format: neteyes_{channel}_{action}
    # channel may contain underscore (e.g. none currently, but handle cleanly)
    if len(parts) < 3:
        return {
            "content": [{"type": "text", "text": f"Malformed tool name: {name}"}],
            "isError": True,
        }

    channel_id = parts[1]
    action_name = "_".join(parts[2:])

    result = run_action(channel_id, action_name, **arguments)
    if result.success:
        response_text = result.markdown or (json.dumps(result.data, indent=2, ensure_ascii=False) if result.data else "Action completed successfully.")
        return {
            "content": [{"type": "text", "text": response_text}],
            "isError": False,
        }
    else:
        error_msg = f"Error executing {channel_id}:{action_name} — {result.error}"
        if result.fallbacks_attempted:
            error_msg += f"\nFallbacks attempted: {' -> '.join(result.fallbacks_attempted)}"
        return {
            "content": [{"type": "text", "text": error_msg}],
            "isError": True,
        }


def process_mcp_message(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process a single JSON-RPC 2.0 MCP request and return response dict (or None for notifications)."""
    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    }
                },
                "serverInfo": {
                    "name": "neteyes-mcp-server",
                    "version": __version__,
                },
            },
        }
    elif method == "notifications/initialized":
        return None
    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {},
        }
    elif method == "tools/list":
        tools = get_mcp_tools()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": tools,
            },
        }
    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        res = handle_tool_call(tool_name, tool_args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": res,
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found",
            },
        }


def run_mcp_server() -> None:
    """Run JSON-RPC 2.0 stdio server for MCP."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except Exception:
                continue

            resp = process_mcp_message(request)
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()

        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            req_id = request.get("id") if "request" in locals() and isinstance(request, dict) else None
            err_resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal MCP server error: {str(e)}",
                },
            }
            sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()

        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": req_id if "req_id" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal MCP server error: {str(e)}",
                },
            }
            sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_mcp_server()
