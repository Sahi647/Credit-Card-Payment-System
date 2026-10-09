from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import (
    Base,
    SessionLocal,
    engine,
)
from .auth_router import auth_router
from .routers import router
from .services import sync_missing_transactions

Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    sync_missing_transactions(db)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app = FastAPI(
    title="Credit Card Payment API",
    description="CardFlow simulated payment API. No real money is charged.",
    version="1.0.0"
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="payment-static",
)
app.include_router(router)
app.include_router(auth_router)

@app.get("/", response_class=HTMLResponse)
def payment_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="payment.html",
        context={},
    )

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "Credit Card Payment API"
    }