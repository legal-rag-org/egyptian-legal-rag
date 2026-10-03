# insurance-pension-rag

An intelligent RAG-based assistant for social insurance and pension information, providing accurate answers from trusted sources.

## Requirements

* Python 3.11 or later
* [uv](https://docs.astral.sh/uv/)

## Installation

### Install uv

If you don't have `uv` installed, install it using:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then verify the installation:

```bash
uv --version
```

### Clone the repository

```bash
git clone https://github.com/Ahmed-KKhaled/egyptian-legal-rag.git
cd egyptian-legal-rag
```

### Create the virtual environment and install dependencies

```bash
uv sync
```

This will create the project's virtual environment and install all dependencies specified in `pyproject.toml`.

### Activate the virtual environment

You can activate the environment manually:

```bash
source .venv/bin/activate
```

Or simply run project commands through `uv` without activating the environment:

```bash
uv run <command>
```

### Setup your command line interface for better readability

```bash
export PS1="\\[\033[01;32m\\]\u@\h:\w\n\\[\033[00m\\]\\$ "
```

## Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Set your environment variables in the `.env` file, such as:

```env
OPENAI_API_KEY=your_api_key
```

## Run Docker Compose Services

```bash
cd docker
cp .env.example .env
```

Update `.env` with your credentials.

Then start the Docker Compose services:

```bash
sudo docker compose up -d
```

## Run the FastAPI Server

From the `src` directory:

```bash
cd src
uv run uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

The API will be available at:

```text
http://localhost:5000
```

Swagger API documentation:

```text
http://localhost:5000/docs
```
