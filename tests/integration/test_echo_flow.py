import re
import socket
import threading
import time
from collections.abc import Iterator

import httpx
import pytest
import uvicorn

from localinteractiveairesponder.app import app


def extract_stream_url(html: str) -> str:
    match = re.search(r'sse-connect="([^"]+)"', html)
    assert match is not None
    return match.group(1)


@pytest.fixture(scope="module")
def live_server() -> Iterator[str]:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("127.0.0.1", 0))
    server_socket.listen()
    port = server_socket.getsockname()[1]

    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [server_socket]}, daemon=True)
    thread.start()

    deadline = time.monotonic() + 5
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=2)
        server_socket.close()
        raise RuntimeError("The integration test server did not start")

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)
    server_socket.close()


def test_chat_page_uses_response_provider_and_streams_five_chunks(live_server: str) -> None:
    with httpx.Client(base_url=live_server, timeout=10) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert 'hx-post="/chat"' in page.text
        assert 'hx-target="#chat-messages"' in page.text
        assert "htmx-ext-sse" in page.text

        assert client.post("/echo", data={"message": "hello"}).status_code == 404

        start = client.post("/chat", data={"message": "hello <world>"})

        assert start.status_code == 200
        assert "hello &lt;world&gt;" in start.text
        assert 'sse-swap="chunk"' in start.text
        assert 'hx-swap="beforeend"' in start.text
        stream_url = extract_stream_url(start.text)

        chunks = []
        arrival_times = []
        event_names = []
        current_event = None
        with client.stream("GET", stream_url) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            for line in response.iter_lines():
                if line.startswith("event: "):
                    current_event = line.removeprefix("event: ")
                    event_names.append(current_event)
                elif line.startswith("data: ") and current_event == "chunk":
                    chunks.append(line.removeprefix("data: "))
                    arrival_times.append(time.monotonic())

        expected = '<span class="echo-line">hello &lt;world&gt;</span><br>'
        assert chunks == [expected] * 5
        assert len(arrival_times) == 5
        assert all(later - earlier >= 0.2 for earlier, later in zip(arrival_times, arrival_times[1:]))
        assert event_names == ["chunk"] * 5 + ["complete"]


def test_chat_stream_preserves_newlines_and_escapes_html(live_server: str) -> None:
    with httpx.Client(base_url=live_server, timeout=10) as client:
        start = client.post("/chat", data={"message": "first\n<script>alert(1)</script>"})
        stream_url = extract_stream_url(start.text)

        with client.stream("GET", stream_url) as response:
            stream = response.read().decode()

    assert "first&#10;&lt;script&gt;alert(1)&lt;/script&gt;" in stream
    assert "<script>alert(1)</script>" not in stream
