from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from typing import List, Dict, Any
from app.database import get_database
from app.utils.security import ALGORITHM, SECRET_KEY, get_current_user
from jose import jwt, JWTError
from bson import ObjectId
from datetime import datetime

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, workspace_id: str):
        await websocket.accept()
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = []
        self.active_connections[workspace_id].append(websocket)

    def disconnect(self, websocket: WebSocket, workspace_id: str):
        if workspace_id in self.active_connections:
            if websocket in self.active_connections[workspace_id]:
                self.active_connections[workspace_id].remove(websocket)
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]

    async def broadcast_to_workspace(self, message: str, workspace_id: str, sender_id: str = None, sender_name: str = None):
        if workspace_id not in self.active_connections:
            return
        import json
        payload = {
            "type": "chat",
            "workspace_id": workspace_id,
            "text": message,
            "timestamp": datetime.utcnow().isoformat(),
            "sender_id": sender_id or "",
            "sender_name": sender_name or "",
        }
        json_payload = json.dumps(payload)
        dead = []
        for connection in list(self.active_connections.get(workspace_id, [])):
            try:
                await connection.send_text(json_payload)
            except Exception:
                dead.append(connection)
        for d in dead:
            try:
                self.active_connections[workspace_id].remove(d)
            except ValueError:
                pass

    async def broadcast_event(self, workspace_id: str, event_type: str, extra: dict = None):
        """Broadcast a typed non-chat event (e.g. budget_update, expense_update)
        to all WebSocket connections in the given workspace."""
        if workspace_id not in self.active_connections:
            return
        import json
        payload = {
            "type": event_type,
            "workspace_id": workspace_id,
            "timestamp": datetime.utcnow().isoformat(),
            **(extra or {}),
        }
        json_payload = json.dumps(payload)
        dead = []
        for connection in list(self.active_connections.get(workspace_id, [])):
            try:
                await connection.send_text(json_payload)
            except Exception:
                dead.append(connection)
        for d in dead:
            try:
                self.active_connections[workspace_id].remove(d)
            except ValueError:
                pass

manager = ConnectionManager()


async def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        username = payload.get("sub")
        if user_id is None:
            return None
        return {"user_id": user_id, "username": username}
    except JWTError:
        return None


@router.websocket("/ws/{workspace_id}")
async def websocket_endpoint(websocket: WebSocket, workspace_id: str, token: str = Query(...)):
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=1008)
        return

    db = get_database()
    try:
        w_id = ObjectId(workspace_id)
    except Exception:
        await websocket.close(code=1008)
        return

    workspace = await db.workspaces.find_one({"_id": w_id})
    if not workspace or not any(m["user_id"] == user["user_id"] for m in workspace.get("members", [])):
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, workspace_id)
    try:
        while True:
            data = await websocket.receive_text()

            message_doc = {
                "workspace_id": workspace_id,
                "sender_id": user["user_id"],
                "sender_name": user["username"],
                "text": data,
                "timestamp": datetime.utcnow(),
            }
            await db.messages.insert_one(message_doc)

            await manager.broadcast_to_workspace(
                message=data,
                workspace_id=workspace_id,
                sender_id=user["user_id"],
                sender_name=user["username"],
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, workspace_id)
    except Exception:
        manager.disconnect(websocket, workspace_id)


@router.get("/history/{workspace_id}")
async def get_chat_history(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """
    Returns stored chat history for a workspace.
    Uses standard Bearer-token auth (Authorization header) so normal axios calls work.
    """
    db = get_database()

    try:
        w_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    workspace = await db.workspaces.find_one({"_id": w_id})
    if not workspace or not any(
        m["user_id"] == current_user["user_id"] for m in workspace.get("members", [])
    ):
        raise HTTPException(status_code=403, detail="Not authorized")

    cursor = db.messages.find({"workspace_id": workspace_id}).sort("timestamp", 1).limit(200)
    raw = await cursor.to_list(length=200)

    result = []
    for m in raw:
        ts = m.get("timestamp")
        result.append({
            "_id": str(m["_id"]),
            "workspace_id": m.get("workspace_id", ""),
            "sender_id": m.get("sender_id", ""),
            "sender_name": m.get("sender_name", "Unknown"),
            "text": m.get("text", ""),
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts or ""),
        })

    return result
