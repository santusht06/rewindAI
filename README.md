# rewindAI

![AI Maintained](https://img.shields.io/badge/readme-AI%20maintained-blue)


## 🚀 Installation

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Run the test suite with `pytest -q`, then start the API with:

```bash
uvicorn services.api.main:app --reload
```

The TV client is available at `http://127.0.0.1:8000/tv/` and the API docs at
`http://127.0.0.1:8000/docs`.
