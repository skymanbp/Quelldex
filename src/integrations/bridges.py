"""
Quelldex Integrations — IDE launch, MarkVue/H5Lens interface
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from typing import Optional


# ── IDE Integration ─────────────────────────────────────────────

class IDELauncher:
    """Launch external IDE editors for code files."""

    KNOWN_IDES = {
        "vscode": {
            "name": "Visual Studio Code",
            "commands": ["code", "code-insiders"],
            "args_file": ["{cmd}", "{file}"],
            "args_folder": ["{cmd}", "{folder}"],
            "args_file_line": ["{cmd}", "--goto", "{file}:{line}"],
        },
        "cursor": {
            "name": "Cursor",
            "commands": ["cursor"],
            "args_file": ["{cmd}", "{file}"],
            "args_folder": ["{cmd}", "{folder}"],
            "args_file_line": ["{cmd}", "--goto", "{file}:{line}"],
        },
        "sublime": {
            "name": "Sublime Text",
            "commands": ["subl", "sublime_text"],
            "args_file": ["{cmd}", "{file}"],
            "args_folder": ["{cmd}", "{folder}"],
            "args_file_line": ["{cmd}", "{file}:{line}"],
        },
        "vim": {
            "name": "Vim (Terminal)",
            "commands": ["vim", "nvim", "gvim"],
            "args_file": ["{cmd}", "{file}"],
            "args_folder": ["{cmd}", "{folder}"],
            "args_file_line": ["{cmd}", "+{line}", "{file}"],
        },
    }

    def __init__(self, custom_path: str = ""):
        self.custom_path = custom_path
        self._detected = {}

    def detect_installed(self) -> dict:
        """Detect which IDEs are available on this system."""
        self._detected = {}
        for ide_id, info in self.KNOWN_IDES.items():
            for cmd in info["commands"]:
                path = shutil.which(cmd)
                if path:
                    self._detected[ide_id] = {
                        "name": info["name"],
                        "command": cmd,
                        "path": path,
                    }
                    break
        # Add custom IDE if set
        if self.custom_path and os.path.isfile(self.custom_path):
            self._detected["custom"] = {
                "name": Path(self.custom_path).stem,
                "command": self.custom_path,
                "path": self.custom_path,
            }
        return self._detected

    def get_available(self) -> list:
        """Return list of available IDE options."""
        if not self._detected:
            self.detect_installed()
        return [
            {"id": k, "name": v["name"], "path": v["path"]}
            for k, v in self._detected.items()
        ]

    def open_file(self, filepath: str, ide_id: str = "vscode", line: int = None) -> bool:
        """Open a file in the specified IDE."""
        if not self._detected:
            self.detect_installed()

        if ide_id not in self._detected and ide_id != "custom":
            # Fallback: try opening with system default
            return self._open_system_default(filepath)

        if ide_id == "custom":
            cmd = self.custom_path
            try:
                subprocess.Popen([cmd, filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                return False

        info = self.KNOWN_IDES.get(ide_id, {})
        cmd = self._detected[ide_id]["command"]

        try:
            if line and "args_file_line" in info:
                args = [a.format(cmd=cmd, file=filepath, line=line) for a in info["args_file_line"]]
            else:
                args = [a.format(cmd=cmd, file=filepath) for a in info["args_file"]]
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return self._open_system_default(filepath)

    def open_folder(self, folderpath: str, ide_id: str = "vscode") -> bool:
        """Open a folder/project in the IDE."""
        if not self._detected:
            self.detect_installed()

        if ide_id == "custom":
            cmd = self.custom_path
        elif ide_id in self._detected:
            cmd = self._detected[ide_id]["command"]
        else:
            return self._open_system_default(folderpath)

        info = self.KNOWN_IDES.get(ide_id, {})
        try:
            if "args_folder" in info:
                args = [a.format(cmd=cmd, folder=folderpath) for a in info["args_folder"]]
            else:
                args = [cmd, folderpath]
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def _open_system_default(self, filepath: str) -> bool:
        """Open with OS default application."""
        try:
            if sys.platform == "win32":
                os.startfile(filepath)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", filepath])
            else:
                subprocess.Popen(["xdg-open", filepath])
            return True
        except Exception:
            return False


# ── MarkVue / H5Lens Integration Interface ──────────────────────

class ExternalToolBridge:
    """
    Generic bridge for external Quelldex-compatible tools.
    
    Protocol: JSON-based message passing via stdin/stdout or socket.
    Tools register capabilities and Quelldex dispatches files to them.
    
    Designed for MarkVue (Markdown viewer) and H5Lens (HDF5 viewer)
    but works with any tool that implements the protocol.
    """

    def __init__(self):
        self.registered_tools = {}

    def register_tool(self, tool_id: str, config: dict):
        """
        Register an external tool.
        
        config = {
            "name": "MarkVue",
            "executable": "/path/to/markvue",
            "supported_ext": [".md", ".markdown"],
            "protocol": "cli",        # "cli" | "socket" | "pipe"
            "args_template": "{exe} --file {file}",
            "port": None,             # For socket protocol
        }
        """
        self.registered_tools[tool_id] = {
            "name": config.get("name", tool_id),
            "executable": config.get("executable", ""),
            "supported_ext": set(config.get("supported_ext", [])),
            "protocol": config.get("protocol", "cli"),
            "args_template": config.get("args_template", "{exe} {file}"),
            "port": config.get("port"),
            "enabled": True,
        }

    def unregister_tool(self, tool_id: str):
        self.registered_tools.pop(tool_id, None)

    def get_tool_for_file(self, filepath: str) -> Optional[str]:
        """Find the best registered tool for a file extension."""
        ext = Path(filepath).suffix.lower()
        for tid, tool in self.registered_tools.items():
            if tool["enabled"] and ext in tool["supported_ext"]:
                return tid
        return None

    def launch_tool(self, tool_id: str, filepath: str, extra_args: dict = None) -> bool:
        """Launch a registered tool with a file."""
        tool = self.registered_tools.get(tool_id)
        if not tool or not tool["enabled"]:
            return False

        exe = tool["executable"]
        if not exe or not os.path.isfile(exe):
            # Try finding in PATH
            found = shutil.which(exe) or shutil.which(tool["name"].lower())
            if found:
                exe = found
            else:
                return False

        try:
            if tool["protocol"] == "cli":
                cmd_str = tool["args_template"].format(exe=exe, file=filepath)
                if extra_args:
                    for k, v in extra_args.items():
                        cmd_str += f" --{k} {v}"
                subprocess.Popen(
                    cmd_str.split(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            elif tool["protocol"] == "socket":
                return self._send_socket_message(tool, {
                    "action": "open",
                    "file": filepath,
                    **(extra_args or {}),
                })
        except Exception:
            return False
        return False

    def _send_socket_message(self, tool: dict, message: dict) -> bool:
        """Send a JSON message to a tool via socket."""
        import socket
        port = tool.get("port", 0)
        if not port:
            return False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect(("127.0.0.1", port))
                s.sendall(json.dumps(message).encode() + b"\n")
                return True
        except Exception:
            return False

    def get_registered_tools(self) -> list:
        return [
            {"id": k, **{kk: vv for kk, vv in v.items() if kk != "supported_ext"}, 
             "supported_ext": list(v["supported_ext"])}
            for k, v in self.registered_tools.items()
        ]

    def save_config(self, filepath: str):
        """Save tool registrations to JSON."""
        data = {}
        for tid, tool in self.registered_tools.items():
            data[tid] = {k: (list(v) if isinstance(v, set) else v) for k, v in tool.items()}
        Path(filepath).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def load_config(self, filepath: str):
        """Load tool registrations from JSON."""
        p = Path(filepath)
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            for tid, tool in data.items():
                tool["supported_ext"] = set(tool.get("supported_ext", []))
                self.registered_tools[tid] = tool
        except Exception:
            pass
