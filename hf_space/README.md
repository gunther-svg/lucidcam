---
title: LucidCam Lucy-Edit Backend
emoji: 🎥
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
hardware: a10g-small
sleep_time_seconds: 300
private: true
---

# LucidCam — Lucy-Edit-Dev Inference Backend

This is the private compute backend for the **LucidCam** desktop application.

It runs [`decart-ai/Lucy-Edit-Dev`](https://huggingface.co/decart-ai/Lucy-Edit-Dev) on an **NVIDIA A10G (24 GB VRAM)** and exposes a REST API that the local LucidCam client uses to process sliding-window video frame chunks.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Returns `{"status": "ready"}` when model is loaded, `"loading"` during warm-up |
| `/infer` | POST | Accepts `multipart/form-data` with `frames[]` (JPEG bytes) + `prompt` string. Returns processed frames as base64 JSON. |

## Hardware

- **GPU**: NVIDIA A10G — 24 GB VRAM
- **Precision**: `bfloat16`
- **Sleep**: Auto-pauses after 5 minutes of inactivity

## Access

This Space is **private**. All API calls require an `Authorization: Bearer <HF_TOKEN>` header.

## License

Model weights are used under the [Lucy-Edit-Dev Non-Commercial License](https://drive.google.com/file/d/1pX34A-UOEl9CErMUZKdKzhoWhtSI1TJK/view). Personal/research use only.
