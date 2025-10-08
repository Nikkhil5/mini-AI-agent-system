from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from db import list_reports, get_report, init_db
from agent import run_agent_for_query
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

init_db()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

if not SERPAPI_API_KEY:
    print("⚠️ Warning: SERPAPI_API_KEY not set")
if not HUGGINGFACE_API_KEY:
    print("⚠️ Warning: HUGGINGFACE_API_KEY not set")

app = FastAPI(title="AI Research Agent")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

os.makedirs(os.path.join(BASE_DIR, "templates"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)

try:
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
except Exception:
    pass


@app.get("/")
async def root():
    return {"message": "AI Research Agent is running"}


@app.post("/query", response_class=HTMLResponse)
async def submit_query(request: Request, query: str = Form(...)):
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, run_agent_for_query, query)
        if result.get("success"):
            return RedirectResponse(url=f"/report/{result['report_id']}", status_code=303)
        else:
            reports = list_reports()
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "reports": reports, "error": result.get("error", "Unknown error")})
    except Exception as e:
        reports = list_reports()
        return templates.TemplateResponse(
            "index.html", {"request": request, "reports": reports, "error": str(e)})


@app.get("/report/{report_id}", response_class=HTMLResponse)
async def view_report(request: Request, report_id: int):
    rep = get_report(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    return templates.TemplateResponse("report.html", {"request": request, "r": rep})


@app.get("/health")
async def health():
    return {"status": "ok", "message": "AI Research Agent is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
