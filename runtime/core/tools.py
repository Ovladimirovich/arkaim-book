class ToolExecutor:
    async def run(self, tool: str, args: dict) -> dict:
        return {"tool": tool, "status": "ok", "args": args}
