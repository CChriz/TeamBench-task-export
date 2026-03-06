# O8: Dockerfile Fix

## Goal
Fix a broken `Dockerfile` for a Python web application so that it builds
correctly and the container serves the app on the correct port.

## Hard Requirements

1. **Base image tag**: The Dockerfile uses a non-existent tag. Fix to use the correct Python slim tag.
2. **Layer ordering**: `COPY . .` appears before `RUN pip install -r requirements.txt`. The dependency install must happen before copying app code (for cache efficiency), and requirements.txt must be copied first.
3. **Port mismatch**: The `EXPOSE` directive exposes the wrong port. The app (in `app.py`) listens on a specific port — match it.
4. **Missing WORKDIR**: Add a `WORKDIR /app` directive before any COPY/RUN commands.
5. **CMD format**: The CMD uses shell form. Convert to exec form `["python", "app.py"]`.

## Deliverables
- Fixed `Dockerfile`
- Verifier confirms all 5 issues resolved.
