from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "working"}

@app.post("/test-login")
def test_login():
    return {"message": "login endpoint works"}
