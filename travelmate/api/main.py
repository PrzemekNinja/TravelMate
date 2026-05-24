from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from travelmate.services.planner_service import PlannerEventCallback, PlannerService
from travelmate.tools.logging_utils import AgentNameFormatter, get_travelmate_logger

APP_TITLE = "TravelMate AI PWA"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "travelmate" / "web"
OUTPUT_ROOT = PROJECT_ROOT / "output"
AGENT_SEQUENCE = [
    "profile_agent",
    "transport_agent",
    "geo_agent",
    "itinerary_agent",
    "verification_agent",
    "formatter_agent",
]
STATUS_IDLE = "IDLE"
STATUS_PROCESSING = "PROCESSING"
STATUS_DONE = "DONE"
STATUS_ERROR = "ERROR"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class ChatAcceptedResponse(BaseModel):
    accepted: bool
    session_id: str
    status: str


class ThreadIdFilter(logging.Filter):
    def __init__(self, thread_id: int) -> None:
        super().__init__()
        self._thread_id = thread_id

    def filter(self, record: logging.LogRecord) -> bool:
        return record.thread == self._thread_id


@dataclass(slots=True)
class ChatSession:
    session_id: str
    loop: asyncio.AbstractEventLoop
    events: list[dict[str, Any]] = field(default_factory=list)
    listeners: set[asyncio.Queue[dict[str, Any]]] = field(default_factory=set)
    agent_statuses: dict[str, str] = field(
        default_factory=lambda: {agent: STATUS_IDLE for agent in AGENT_SEQUENCE}
    )
    agent_started_at: dict[str, float | None] = field(
        default_factory=lambda: {agent: None for agent in AGENT_SEQUENCE}
    )
    agent_elapsed_seconds: dict[str, float | None] = field(
        default_factory=lambda: {agent: None for agent in AGENT_SEQUENCE}
    )
    current_agent_index: int = -1
    state: str = "idle"
    task: asyncio.Task[None] | None = None

    async def publish(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        if len(self.events) > 500:
            self.events[:] = self.events[-500:]
        stale: list[asyncio.Queue[dict[str, Any]]] = []
        for listener in self.listeners:
            try:
                listener.put_nowait(event)
            except asyncio.QueueFull:
                stale.append(listener)
        for listener in stale:
            self.listeners.discard(listener)

    def publish_threadsafe(self, event: dict[str, Any]) -> None:
        self.loop.call_soon_threadsafe(lambda: asyncio.create_task(self.publish(event)))

    async def snapshot(self) -> list[dict[str, Any]]:
        return list(self.events)

    async def register_listener(self) -> tuple[asyncio.Queue[dict[str, Any]], list[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
        self.listeners.add(queue)
        return queue, list(self.events)

    def unregister_listener(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.listeners.discard(queue)

    def _build_agent_payload(self) -> dict[str, Any]:
        return {
            "type": "agent_statuses",
            "agents": [
                {
                    "name": name,
                    "status": self.agent_statuses[name],
                    "elapsed_seconds": self.agent_elapsed_seconds[name],
                }
                for name in AGENT_SEQUENCE
            ],
        }

    def publish_agent_statuses(self) -> None:
        self.publish_threadsafe(self._build_agent_payload())

    def set_state(self, state: str) -> None:
        self.state = state
        self.publish_threadsafe({"type": "session_status", "status": state})

    def reset_agent_tracking(self) -> None:
        for name in AGENT_SEQUENCE:
            self.agent_statuses[name] = STATUS_IDLE
            self.agent_started_at[name] = None
            self.agent_elapsed_seconds[name] = None
        self.current_agent_index = -1
        self.publish_agent_statuses()

    def _finalize_agent_elapsed(self, agent_name: str, finished_at: float) -> None:
        started = self.agent_started_at.get(agent_name)
        if started is None:
            return
        if self.agent_elapsed_seconds.get(agent_name) is None:
            self.agent_elapsed_seconds[agent_name] = max(0.0, finished_at - started)

    def mark_agent_processing(self, agent_name: str) -> None:
        if agent_name not in self.agent_statuses:
            return

        now = time.perf_counter()
        agent_index = AGENT_SEQUENCE.index(agent_name)

        if self.current_agent_index >= 0 and agent_index > self.current_agent_index:
            for done_index in range(self.current_agent_index, agent_index):
                done_agent = AGENT_SEQUENCE[done_index]
                self._finalize_agent_elapsed(done_agent, now)

        self.current_agent_index = max(self.current_agent_index, agent_index)
        for index, name in enumerate(AGENT_SEQUENCE):
            if index < agent_index:
                self.agent_statuses[name] = STATUS_DONE
            elif index == agent_index:
                self.agent_statuses[name] = STATUS_PROCESSING
                if self.agent_started_at[name] is None:
                    self.agent_started_at[name] = now
            elif self.agent_statuses[name] != STATUS_ERROR:
                self.agent_statuses[name] = STATUS_IDLE
        self.publish_agent_statuses()

    def mark_all_done(self) -> None:
        now = time.perf_counter()
        for name in AGENT_SEQUENCE:
            self._finalize_agent_elapsed(name, now)
            self.agent_statuses[name] = STATUS_DONE
        self.publish_agent_statuses()

    def mark_error(self, agent_name: str | None = None) -> None:
        now = time.perf_counter()
        if agent_name and agent_name in self.agent_statuses:
            target_agent = agent_name
        elif self.current_agent_index >= 0:
            target_agent = AGENT_SEQUENCE[self.current_agent_index]
        else:
            target_agent = AGENT_SEQUENCE[0]

        self._finalize_agent_elapsed(target_agent, now)
        self.agent_statuses[target_agent] = STATUS_ERROR
        self.publish_agent_statuses()


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: str | None = None) -> ChatSession:
        async with self._lock:
            session_key = session_id or uuid.uuid4().hex
            if session_key not in self._sessions:
                self._sessions[session_key] = ChatSession(
                    session_id=session_key,
                    loop=asyncio.get_running_loop(),
                )
                await self._sessions[session_key].publish(
                    {"type": "session_status", "status": "idle", "session_id": session_key}
                )
                await self._sessions[session_key].publish(self._sessions[session_key]._build_agent_payload())
            return self._sessions[session_key]

    async def get(self, session_id: str) -> ChatSession | None:
        async with self._lock:
            return self._sessions.get(session_id)


class SessionLogHandler(logging.Handler):
    def __init__(self, session: ChatSession, thread_id: int) -> None:
        super().__init__(level=logging.INFO)
        self._session = session
        self.addFilter(ThreadIdFilter(thread_id))
        self.setFormatter(
            AgentNameFormatter(
                fmt="[%(agent_name)s] %(asctime)s %(levelname)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            formatted = self.format(record)
            agent_name = getattr(record, "agent_name", record.name.split(".")[-1])
            if agent_name in AGENT_SEQUENCE:
                if record.levelno >= logging.ERROR:
                    self._session.mark_error(agent_name)
                else:
                    self._session.mark_agent_processing(agent_name)

            self._session.publish_threadsafe(
                {
                    "type": "log_entry",
                    "level": record.levelname,
                    "agent": agent_name,
                    "message": formatted,
                    "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                }
            )
        except Exception:
            self.handleError(record)


app = FastAPI(title=APP_TITLE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
store = SessionStore()


def _debug_event_publisher(session: ChatSession) -> PlannerEventCallback:
    def emit(event: dict[str, Any]) -> None:
        session.publish_threadsafe(event)

    return emit


def _run_planner_sync(session: ChatSession, message: str) -> None:
    thread_id = threading.get_ident()
    logger = get_travelmate_logger()
    handler = SessionLogHandler(session=session, thread_id=thread_id)
    logger.addHandler(handler)

    try:
        session.set_state("running")
        session.mark_agent_processing(AGENT_SEQUENCE[0])
        service = PlannerService()
        result = service.run(
            user_text=message,
            output_root=OUTPUT_ROOT,
            event_callback=_debug_event_publisher(session),
        )
        session.mark_all_done()
        session.publish_threadsafe(
            {
                "type": "chat_message",
                "role": "assistant",
                "content": result.markdown_plan,
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        session.publish_threadsafe(
            {
                "type": "final_result",
                "destination": result.parsed.request.destination,
                "days": result.parsed.request.days,
                "html_output_path": str(result.html_output_path),
                "map_output_path": str(result.map_output_path) if result.map_output_path else None,
            }
        )
        session.set_state("completed")
    except Exception as exc:
        session.mark_error()
        session.publish_threadsafe(
            {
                "type": "chat_message",
                "role": "assistant",
                "content": "Wystąpił błąd podczas generowania planu. Sprawdź `Admin_View` po szczegóły.",
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        session.publish_threadsafe(
            {
                "type": "error",
                "message": str(exc),
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        session.set_state("error")
        raise
    finally:
        logger.removeHandler(handler)
        handler.close()


async def _run_planner(session: ChatSession, message: str) -> None:
    try:
        await asyncio.to_thread(_run_planner_sync, session, message)
    except Exception:
        return
    finally:
        session.task = None


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/manifest.json")
async def manifest() -> FileResponse:
    return FileResponse(WEB_ROOT / "manifest.json", media_type="application/manifest+json")


@app.get("/service-worker.js")
async def service_worker() -> FileResponse:
    return FileResponse(WEB_ROOT / "service-worker.js", media_type="application/javascript")


@app.get("/icon.svg")
async def icon() -> FileResponse:
    return FileResponse(WEB_ROOT / "icon.svg", media_type="image/svg+xml")


@app.post("/chat", response_model=ChatAcceptedResponse)
async def chat(payload: ChatRequest) -> ChatAcceptedResponse:
    session = await store.get_or_create(payload.session_id)

    if session.task and not session.task.done():
        raise HTTPException(status_code=409, detail="Ta sesja nadal przetwarza poprzednią wiadomość.")

    await session.publish(
        {
            "type": "chat_message",
            "role": "user",
            "content": payload.message,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
    )
    session.reset_agent_tracking()
    session.set_state("queued")
    session.task = asyncio.create_task(_run_planner(session, payload.message))
    return ChatAcceptedResponse(accepted=True, session_id=session.session_id, status="queued")


@app.websocket("/admin/logs")
async def admin_logs(websocket: WebSocket, session_id: str = Query(...)) -> None:
    await websocket.accept()
    session = await store.get_or_create(session_id)
    queue, history = await session.register_listener()

    try:
        for event in history:
            await websocket.send_json(event)
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    finally:
        session.unregister_listener(queue)
        with contextlib.suppress(RuntimeError):
            await websocket.close()


def main() -> None:
    uvicorn.run("travelmate.api.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
