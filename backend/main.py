from fastapi import FastAPI

app = FastAPI(title="UPSC Copy Checker API")


@app.get("/")
def root():
    return {"message": "UPSC Copy Checker API is running"}