from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_CONTENT = (
    "RAG 是检索增强生成技术。它先从外部知识库检索与用户问题相关的片段，"
    "再把这些片段和问题一起交给大模型生成回答。RAG 的价值在于降低幻觉、"
    "补充模型训练后才出现的新知识，并让回答可以追溯到资料来源。"
)


@dataclass(frozen=True)
class CheckConfig:
    base_url: str
    anonymous_id: str
    keep_record: bool


class CheckFailed(RuntimeError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the M0 quiz -> report -> MySQL history acceptance check.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Running backend base URL.")
    parser.add_argument("--anonymous-id", default="", help="Anonymous ID used for the history check.")
    parser.add_argument("--keep-record", action="store_true", help="Keep the generated history record after success.")
    args = parser.parse_args()

    config = CheckConfig(
        base_url=args.base_url.rstrip("/"),
        anonymous_id=args.anonymous_id or f"self_check_{int(time.time())}",
        keep_record=args.keep_record,
    )

    try:
        run_check(config)
    except CheckFailed as exc:
        print(f"[fail] {exc}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"[fail] Backend is unreachable at {config.base_url}: {exc}", file=sys.stderr)
        return 1
    return 0


def run_check(config: CheckConfig) -> None:
    print(f"[1/6] health: {config.base_url}/health")
    health = request_json(config, "GET", "/health")
    if health.get("status") != "ok":
        raise CheckFailed(f"Unexpected health response: {health}")
    if health.get("historyDatabase") is not True:
        raise CheckFailed("historyDatabase is not true. Set DATABASE_URL, run migrations, and restart the backend.")

    print("[2/6] generate quiz")
    quiz_body = {
        "sourceType": "text",
        "content": DEFAULT_CONTENT,
        "questionCount": 3,
        "questionTypes": ["single_choice", "true_false"],
        "difficulty": "normal",
    }
    quiz_response = api_data(request_json(config, "POST", "/api/v1/quiz/generate", quiz_body))
    quiz = quiz_response.get("quiz") or {}
    provider = str(quiz_response.get("provider") or quiz.get("modelProvider") or "unknown")
    questions = quiz.get("questions") or []
    if len(questions) != 3:
        raise CheckFailed(f"Expected 3 questions, got {len(questions)}")

    print("[3/6] generate report")
    answers = build_answers(questions)
    report_response = api_data(
        request_json(
            config,
            "POST",
            "/api/v1/reports/generate",
            {"quizId": quiz["quizId"], "questions": questions, "answers": answers, "duration": 24},
        )
    )
    report = report_response.get("report") or {}
    if report.get("quizId") != quiz["quizId"]:
        raise CheckFailed("Report quizId does not match generated quiz.")

    print("[4/6] save history")
    save_response = api_data(
        request_json(
            config,
            "POST",
            "/api/v1/history",
            {
                "anonymousId": config.anonymous_id,
                "historyId": quiz["quizId"],
                "sourceContent": DEFAULT_CONTENT,
                "quiz": quiz,
                "answers": answers,
                "report": report,
                "provider": provider,
                "questionCount": quiz.get("questionCount") or len(questions),
                "accuracy": report.get("accuracy") or 0,
                "score": report.get("score") or 0,
            },
        )
    )
    record = save_response.get("record") or {}
    history_id = str(record.get("historyId") or "")
    if history_id != quiz["quizId"]:
        raise CheckFailed("Saved historyId does not match generated quizId.")

    print("[5/6] list history")
    list_response = api_data(
        request_json(config, "GET", f"/api/v1/history?anonymousId={urllib.parse.quote(config.anonymous_id)}")
    )
    records = list_response.get("records") or []
    if not any(item.get("historyId") == history_id for item in records):
        raise CheckFailed("Saved record was not found in history list.")

    print("[6/6] get history detail")
    detail_response = api_data(
        request_json(
            config,
            "GET",
            f"/api/v1/history/{urllib.parse.quote(history_id)}?anonymousId={urllib.parse.quote(config.anonymous_id)}",
        )
    )
    detail = detail_response.get("record") or {}
    if detail.get("report", {}).get("reportId") != report.get("reportId"):
        raise CheckFailed("History detail did not preserve the generated report.")

    if not config.keep_record:
        request_json(
            config,
            "DELETE",
            f"/api/v1/history/{urllib.parse.quote(history_id)}?anonymousId={urllib.parse.quote(config.anonymous_id)}",
        )

    action = "kept" if config.keep_record else "deleted after verification"
    print(f"[ok] history self-check passed: historyId={history_id}, anonymousId={config.anonymous_id}, record={action}")


def build_answers(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    answers: list[dict[str, Any]] = []
    for index, question in enumerate(questions):
        correct = str(question["answer"])
        selected = correct
        if index == len(questions) - 1:
            selected = first_wrong_option(question, correct)
        answers.append(
            {
                "questionId": question["id"],
                "selectedOption": selected,
                "isCorrect": selected == correct,
                "duration": 8 + index,
            }
        )
    return answers


def first_wrong_option(question: dict[str, Any], correct: str) -> str:
    for option in question.get("options") or []:
        option_id = str(option.get("id") or "")
        if option_id and option_id != correct:
            return option_id
    return correct


def api_data(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("success") is not True:
        raise CheckFailed(f"API returned an error: {response}")
    data = response.get("data")
    if not isinstance(data, dict):
        raise CheckFailed(f"API returned invalid data: {response}")
    return data


def request_json(config: CheckConfig, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        config.base_url + path,
        data=payload,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise CheckFailed(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
