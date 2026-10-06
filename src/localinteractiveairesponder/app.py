import asyncio
import html
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Local Interactive AI Responder")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
ECHO_REPEAT_COUNT = 5
ECHO_DELAY_SECONDS = 0.3


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@app.post("/echo", response_class=HTMLResponse)
async def start_echo(
    request: Request,
    message: str = Form(min_length=1, max_length=2000),
) -> HTMLResponse:
    stream_url = f"/echo/stream?message={quote(message, safe='')}"
    return templates.TemplateResponse(
        request,
        "echo_stream.html",
        {"stream_url": stream_url},
    )


@app.get("/echo/stream")
async def echo_stream(message: str) -> StreamingResponse:
    async def events():
        escaped_message = (
            html.escape(message)
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\n", "&#10;")
        )
        for _ in range(ECHO_REPEAT_COUNT):
            await asyncio.sleep(ECHO_DELAY_SECONDS)
            yield f'event: chunk\ndata: <span class="echo-line">{escaped_message}</span><br>\n\n'
        yield "event: complete\ndata: done\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
