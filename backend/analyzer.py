import os
import asyncio
from fastapi import WebSocket
from collections import defaultdict

async def get_dir_size_ws(websocket: WebSocket, start_path: str):
    """
    Recursively calculates directory size and streams progress via WebSocket.
    """
    total_size = 0
    tree = {"name": os.path.basename(start_path) or start_path, "path": start_path, "value": 0, "children": []}
    
    # We will only go a few levels deep for the visualization to avoid overwhelming the frontend
    # but we will calculate the full size.
    MAX_DEPTH = 3
    
    async def scan_dir(path, depth=0):
        nonlocal total_size
        node_size = 0
        children = []
        
        try:
            with os.scandir(path) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            size = entry.stat(follow_symlinks=False).st_size
                            node_size += size
                            total_size += size
                            
                            # Stream an update every 50MB to keep UI alive
                            if total_size % (50 * 1024 * 1024) < 100000:
                                await websocket.send_json({"type": "progress", "scanned_bytes": total_size})
                                await asyncio.sleep(0) # Yield control
                                
                            children.append({"name": entry.name, "path": entry.path, "value": size, "children": []})
                                
                        elif entry.is_dir(follow_symlinks=False):
                            # Skip protected/unreadable paths
                            if not os.access(entry.path, os.R_OK):
                                continue
                                
                            child_node = await scan_dir(entry.path, depth + 1)
                            node_size += child_node["value"]
                            
                            if depth < MAX_DEPTH and child_node["value"] > 0:
                                children.append(child_node)
                    except (PermissionError, FileNotFoundError, OSError):
                        pass
        except (PermissionError, FileNotFoundError, OSError):
            pass

        # Sort children by size and keep top 10 to avoid massive JSON payloads
        children.sort(key=lambda x: x["value"], reverse=True)
        children = children[:10]

        return {"name": os.path.basename(path) or path, "path": path, "value": node_size, "children": children}

    # Start the scan
    await websocket.send_json({"type": "status", "message": f"Scanning {start_path}..."})
    
    try:
        final_tree = await scan_dir(start_path)
        # Send the final tree
        await websocket.send_json({"type": "complete", "tree": final_tree, "total_bytes": total_size})
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
