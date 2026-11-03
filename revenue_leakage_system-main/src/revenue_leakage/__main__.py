import uvicorn

uvicorn.run("revenue_leakage.service:app", host="0.0.0.0", port=8000)
