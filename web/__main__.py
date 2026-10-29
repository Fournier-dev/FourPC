# atalho pra subir o site com "python -m web", que é o mesmo que rodar
# "uvicorn web.app:app --reload"
import uvicorn

if __name__ == "__main__":
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=True)
