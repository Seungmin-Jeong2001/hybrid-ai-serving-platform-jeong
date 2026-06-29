import os
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="Bastion Alert Relay")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
RELAY_TOKEN = os.getenv("RELAY_TOKEN")


def is_usable_url(value: str | None) -> bool:
    if not value:
        return False
    return value not in {"unknown", "None"}


def classify_alert(payload: dict) -> dict:
    job = str(payload.get("job", "unknown"))
    stage = str(payload.get("stage", "unknown"))
    job_lower = job.lower()

    if job == "sync-harbor-to-ecr" or stage == "model-package":
        return {
            "plane": "HYBRID",
            "title": "Harbor -> ECR 이미지 동기화 실패",
            "emoji": "🚨",
            "color": "#E01E5A",
            "severity": "CRITICAL",
            "intro": (
                "Private -> Public 이미지 전달 과정에서 실패가 발생했습니다.\n"
                "Harbor, ECR 권한, VPN/PrivateLink 경로를 순서대로 확인해 주세요."
            ),
            "guide": "Harbor 인증, AWS ECR 권한, VPN/PrivateLink 경로, ECR Repository 존재 여부를 확인해 주세요.",
        }
    if job == "build-heavy-base" or stage == "build-base":
        return {
            "plane": "PRIVATE",
            "title": "Base Image Build 실패",
            "emoji": "🧱",
            "color": "#E01E5A",
            "severity": "CRITICAL",
            "intro": (
                "담당자 확인이 필요한 CI/CD 실패가 감지되었습니다.\n"
                "Base image build 단계의 실행 로그와 Harbor push 경로를 확인해 주세요."
            ),
            "guide": "Kaniko 실행 로그, Dockerfile.build, Harbor 인증서 및 Push 권한을 확인해 주세요.",
        }
    if job == "trivy-scan" or stage == "security-scan":
        return {
            "plane": "PRIVATE",
            "title": "보안 스캔 단계 실패",
            "emoji": "🛡️",
            "color": "#ECB22E",
            "severity": "WARNING",
            "intro": (
                "담당자 확인이 필요한 보안 스캔 실패가 감지되었습니다.\n"
                "이미지 접근 권한과 취약점 결과를 함께 검토해 주세요."
            ),
            "guide": "Trivy 실행 로그, Harbor 이미지 접근 권한, 취약점 결과를 확인해 주세요.",
        }
    if job == "verify-aws-oidc" or "oidc" in job_lower:
        return {
            "plane": "VERIFY",
            "title": "AWS OIDC 검증 실패",
            "emoji": "🔐",
            "color": "#ECB22E",
            "severity": "WARNING",
            "intro": (
                "OIDC 검증 단계에서 확인이 필요한 실패가 감지되었습니다.\n"
                "운영 경로 전환 전 issuer/JWKS/Trust Policy 조건을 다시 확인해 주세요."
            ),
            "guide": "GitLab OIDC issuer, JWKS 접근성, AWS IAM OIDC Provider, Role Trust Policy의 aud/sub 조건을 확인해 주세요.",
        }
    return {
        "plane": "CI",
        "title": "CI/CD Job 실패",
        "emoji": "⚠️",
        "color": "#E01E5A",
        "severity": "CRITICAL",
        "intro": (
            "담당자 확인이 필요한 CI/CD 실패가 감지되었습니다.\n"
            "아래 요약 정보와 Job 로그를 확인해 주세요."
        ),
        "guide": "GitLab Job 로그와 ci_error_summary 내용을 확인해 주세요.",
    }


def build_action_elements(pipeline_url: str, job_url: str) -> list[dict]:
    elements: list[dict] = []
    if is_usable_url(pipeline_url):
        elements.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Open Pipeline"},
                "url": pipeline_url,
            }
        )
    if is_usable_url(job_url):
        elements.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Open Job Log"},
                "url": job_url,
            }
        )
    return elements


def build_slack_message(payload: dict) -> dict:
    classified = classify_alert(payload)
    occurred_at = payload.get("created_at") or datetime.now(timezone.utc).isoformat()
    summary = str(payload.get("error_summary") or "No error summary provided")[:2500]
    pipeline_url = str(payload.get("pipeline_url", ""))
    job_url = str(payload.get("job_url", ""))
    action_elements = build_action_elements(pipeline_url, job_url)

    fields = [
        {"type": "mrkdwn", "text": f"*Project:*\n{payload.get('project', 'unknown')}"},
        {"type": "mrkdwn", "text": f"*Project Path:*\n`{payload.get('project_path', 'unknown')}`"},
        {"type": "mrkdwn", "text": f"*Plane:*\n{classified['plane']}"},
        {"type": "mrkdwn", "text": f"*Severity:*\n{classified['severity']}"},
        {"type": "mrkdwn", "text": f"*Status:*\n{payload.get('status', 'failed')}"},
        {"type": "mrkdwn", "text": f"*Stage:*\n{payload.get('stage', 'unknown')}"},
        {"type": "mrkdwn", "text": f"*Job:*\n{payload.get('job', 'unknown')}"},
        {"type": "mrkdwn", "text": f"*Branch:*\n{payload.get('branch', 'unknown')}"},
        {"type": "mrkdwn", "text": f"*Commit:*\n{payload.get('commit', 'unknown')}"},
        {"type": "mrkdwn", "text": f"*Pipeline ID:*\n{payload.get('pipeline_id', 'unknown')}"},
        {"type": "mrkdwn", "text": f"*Job ID:*\n{payload.get('job_id', 'unknown')}"},
        {"type": "mrkdwn", "text": f"*Runner:*\n{payload.get('runner_description', 'unknown')}"},
        {"type": "mrkdwn", "text": f"*Runner Tags:*\n{payload.get('runner_tags', 'unknown')}"},
        {"type": "mrkdwn", "text": f"*Occurred At:*\n{occurred_at}"},
    ]

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{classified['emoji']} {classified['title']}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": classified["intro"],
            },
        },
        {
            "type": "section",
            "fields": fields,
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*권장 확인 사항:*\n{classified['guide']}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Error Summary:*\n```{summary}```",
            },
        },
    ]

    if action_elements:
        blocks.append(
            {
                "type": "actions",
                "elements": action_elements,
            }
        )

    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Generated by Bastion Alert Relay at {occurred_at}",
                }
            ],
        }
    )

    return {
        "text": f"{classified['emoji']} {classified['title']} - {payload.get('project', 'unknown')}",
        "attachments": [
            {
                "color": classified["color"],
                "blocks": blocks,
            }
        ],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "alert-relay",
    }


@app.post("/ci-failure")
async def ci_failure(
    request: Request,
    x_relay_token: str | None = Header(default=None),
):
    if not SLACK_WEBHOOK_URL:
        raise HTTPException(
            status_code=500,
            detail="SLACK_WEBHOOK_URL is not set",
        )

    if not RELAY_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="RELAY_TOKEN is not set",
        )

    if x_relay_token != RELAY_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="invalid relay token",
        )

    payload = await request.json()
    slack_message = build_slack_message(payload)

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=slack_message,
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"failed to send slack alert: {exc}",
        )

    return {
        "status": "sent",
        "project": payload.get("project", "unknown"),
        "job": payload.get("job", "unknown"),
    }
