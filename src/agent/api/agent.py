from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from agent.config import settings
from agent.llm.azure import LLMError
from agent.pipeline.messages import serialize_messages
from agent.pipeline.session import AgentSession
from agent.web.jinja_helpers import register_template_globals
from agent.web.uploads import save_product_image

router = APIRouter(tags=["agent"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_DIR))
TEMPLATES.env.globals["store_name"] = settings.store_name
register_template_globals(TEMPLATES.env)


def _agent(request: Request) -> AgentSession:
    session = getattr(request.app.state, "agent_session", None)
    if session is None:
        raise HTTPException(status_code=503, detail="Agent session not initialized")
    return session


@router.post("/api/agent/upload-image")
async def upload_product_image(file: UploadFile = File(...)):
    filename, url = await save_product_image(file)
    return {"filename": filename, "url": url}


@router.get("/app", response_class=HTMLResponse)
async def agent_app(request: Request):
    return TEMPLATES.TemplateResponse(request, "app/index.html", {})


@router.get("/app/gate/{thread_id}", response_class=HTMLResponse)
async def gate_partial(request: Request, thread_id: str):
    agent = _agent(request)
    payload = await agent.get_gate_payload(thread_id)
    return TEMPLATES.TemplateResponse(
        request,
        "app/gate_partial.html",
        {"gate": payload},
    )


def _gate_decision(body: dict) -> dict:
    action = body.get("action")
    if action not in {"approve", "reject", "edit"}:
        raise ValueError("Invalid gate action")

    decision = {
        "action": "approve" if action == "approve" else "reject",
        "comment": body.get("comment", ""),
        "edited_description": body.get("edited_description"),
    }
    if action == "edit":
        if not decision["edited_description"]:
            raise ValueError("edited_description required for edit")
        decision["action"] = "reject"
    return decision


@router.post("/api/agent/{thread_id}/gate")
async def gate_action(request: Request, thread_id: str, body: dict):
    agent = _agent(request)
    try:
        decision = _gate_decision(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = await agent.resume(thread_id, decision)
    return result


@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            try:
                raw = await websocket.receive_text()
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid message format."})
                continue

            agent = getattr(websocket.app.state, "agent_session", None)
            if agent is None:
                await websocket.send_json(
                    {"type": "error", "message": "Agent not ready. Restart the server and refresh."}
                )
                continue

            msg_type = message.get("type")

            if msg_type == "start":
                content = message.get("content", "").strip()
                if not content:
                    await websocket.send_json({"type": "error", "message": "Empty input"})
                    continue
                photo = (message.get("photo_filename") or "").strip() or None
                await websocket.send_json({"type": "processing", "stage": "parse"})
                try:
                    thread_id, payload = await agent.start(content, photo_filename=photo)
                except LLMError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                except Exception as exc:  # noqa: BLE001 — surface to client
                    await websocket.send_json(
                        {"type": "error", "message": f"Pipeline failed: {exc}"}
                    )
                    continue
                await websocket.send_json({"type": "thread", "thread_id": thread_id})
                await websocket.send_json(payload)
                snapshot = await agent.get_messages(thread_id)
                for item in snapshot:
                    await websocket.send_json({"type": "chat", **item})

            elif msg_type == "complete_facts":
                thread_id = message.get("thread_id", "")
                if not thread_id:
                    await websocket.send_json({"type": "error", "message": "Missing thread_id"})
                    continue
                await websocket.send_json({"type": "processing", "stage": "draft"})
                try:
                    result = await agent.resume(
                        thread_id,
                        {
                            "price": message.get("price"),
                            "category": message.get("category"),
                            "name": message.get("name"),
                            "photo_filename": message.get("photo_filename"),
                        },
                    )
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                except Exception as exc:  # noqa: BLE001 — surface to client
                    await websocket.send_json(
                        {"type": "error", "message": f"Pipeline failed: {exc}"}
                    )
                    continue

                await websocket.send_json(result)
                if result.get("type") == "gate":
                    snapshot = await agent.get_messages(thread_id)
                    for item in snapshot[-3:]:
                        await websocket.send_json({"type": "chat", **item})
                elif result.get("type") != "needs_facts":
                    for item in serialize_messages(result.get("messages"))[-2:]:
                        await websocket.send_json({"type": "chat", **item})

            elif msg_type == "gate_action":
                thread_id = message.get("thread_id", "")
                if not thread_id:
                    await websocket.send_json({"type": "error", "message": "Missing thread_id"})
                    continue
                await websocket.send_json({"type": "processing", "stage": "gate"})
                try:
                    decision = _gate_decision(message)
                    result = await agent.resume(thread_id, decision)
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                except Exception as exc:  # noqa: BLE001 — surface to client
                    await websocket.send_json(
                        {"type": "error", "message": f"Gate action failed: {exc}"}
                    )
                    continue

                await websocket.send_json(result)
                if result.get("type") == "gate":
                    snapshot = await agent.get_messages(thread_id)
                    for item in snapshot[-3:]:
                        await websocket.send_json({"type": "chat", **item})
                elif result.get("type") != "needs_facts":
                    for item in serialize_messages(result.get("messages"))[-2:]:
                        await websocket.send_json({"type": "chat", **item})

            elif msg_type == "attach_photo":
                thread_id = message.get("thread_id", "")
                photo = (message.get("photo_filename") or "").strip()
                if not thread_id or not photo:
                    await websocket.send_json(
                        {"type": "error", "message": "thread_id and photo_filename are required"}
                    )
                    continue
                try:
                    result = await agent.attach_photo(thread_id, photo)
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                except Exception as exc:  # noqa: BLE001 — surface to client
                    await websocket.send_json(
                        {"type": "error", "message": f"Could not attach photo: {exc}"}
                    )
                    continue
                await websocket.send_json(result)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json(
                    {"type": "error", "message": f"Unknown message type: {msg_type}"}
                )

    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001 — keep socket alive when possible
        try:
            await websocket.send_json({"type": "error", "message": f"Server error: {exc}"})
        except Exception:  # noqa: BLE001 — socket may already be closed
            return
