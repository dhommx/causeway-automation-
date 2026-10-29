# PIE Automation Portal

## Run the project

Install and start **Docker Engine or Docker Desktop with Docker Compose** first. Docker runs the frontend, API, background worker, and PostgreSQL database; you do not need to install Python or Node.js separately.

The commands below are for **Bash on Linux**, using this checkout's folder. Copy each complete code block into a terminal. The quotation marks around the folder path are required because it contains a space. If you move the project, update that path.

### 1. Start everything

This uses port **3501**, because port 3500 was already occupied on this machine. Keep using the same port in later commands.

```bash
cd "/home/ebrahim/Desktop/PIE/Automation_System/Automation portal" && WEB_PORT=3501 docker compose up -d --build
```

Wait for the command to finish. The first build downloads dependencies and can take several minutes. Database migrations run automatically.

Open **[http://localhost:3501](http://localhost:3501)** in your browser. The services keep running after you close the terminal.

For this local setup, no `.env` file is required: Compose supplies development defaults. If you already have a root `.env`, its database and data-folder settings apply; `WEB_PORT=3501` above overrides its web port.

### 2. Check that it is running

```bash
cd "/home/ebrahim/Desktop/PIE/Automation_System/Automation portal" && WEB_PORT=3501 docker compose ps
curl --fail --show-error http://localhost:3501/api/v1/health
```

All four services (`db`, `api`, `worker`, and `web`) should be up. The health response should contain `"status":"ok"` and `"database":true`. If the API is still starting, wait a few seconds and run the check again.

### Stop the project

```bash
cd "/home/ebrahim/Desktop/PIE/Automation_System/Automation portal" && WEB_PORT=3501 docker compose stop
```

This preserves the database and saved files. To start again, use the command in step 1. Use that same command after changing the code to rebuild the images.

## Troubleshooting

### Port 3501 is already in use

Run on port 3502 instead:

```bash
cd "/home/ebrahim/Desktop/PIE/Automation_System/Automation portal" && WEB_PORT=3502 docker compose up -d --build
```

Then open **http://localhost:3502** and use `WEB_PORT=3502` and port `3502` in subsequent commands and health checks.

### View startup errors

```bash
cd "/home/ebrahim/Desktop/PIE/Automation_System/Automation portal" && WEB_PORT=3501 docker compose logs --tail=100 api worker web db
```

If Docker reports that it cannot connect to the daemon, start Docker and retry. If it reports a socket permission error, use an account authorized to run Docker. If port **5450** is occupied, check whether another PostgreSQL instance or project is using it before changing the database port.

## Saved data and configuration

- PostgreSQL data lives in the Docker volume `db_data`.
- Uploaded files and run outputs live in `./Data` by default (or `DATA_FOLDER` from your root `.env`). Back up both the database and that folder.
- Avoid `docker compose down -v`: it deletes the database volume.
- The default database password and encryption key are public development values. Before deploying to a server, configure a root `.env` using [.env.example](.env.example), with a private database password and a generated encryption key. Preserve the encryption key so stored credentials remain readable.

See [guide.md](guide.md) for configuration details and local development with Python, uv, Node.js, and pnpm.
