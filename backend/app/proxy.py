import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

STREAMLIT_URL = "http://127.0.0.1:8501"

async def proxy_to_streamlit(request: Request, path: str = ""):
    """
    Forwards non-API requests seamlessly to the local Streamlit instance.
    """
    target_url = f"{STREAMLIT_URL}/{path}" if path else STREAMLIT_URL
    if request.url.query:
        target_url += f"?{request.url.query}"

    client = httpx.AsyncClient(base_url=STREAMLIT_URL, timeout=60.0)

    req_headers = dict(request.headers)
    req_headers.pop("host", None)

    req_body = await request.body()

    try:
        upstream_req = client.build_request(
            method=request.method,
            url=target_url,
            headers=req_headers,
            content=req_body
        )
        upstream_res = await client.send(upstream_req, stream=True)

        return StreamingResponse(
            upstream_res.aiter_raw(),
            status_code=upstream_res.status_code,
            headers=dict(upstream_res.headers)
        )
    except Exception as e:
        return Response(content=f"Streamlit warming up... please refresh in a moment. ({str(e)})", status_code=503)