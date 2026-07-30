import time
import uuid
from typing import TYPE_CHECKING

from app.api.schemas import ChatResponse, Citation
from app.db.models import QueryTrace
from app.db.session import SessionLocal
from app.llm.deepseek import DeepSeekError, generate_answer
from app.retrieval.service import RetrievalService
from app.retrieval.types import RetrievedChunk
from app.support.routing import Route, calculate_risk_score, decide_route
from app.support.tickets import ticket_service

if TYPE_CHECKING:
    from app.core.experiment_config import ExperimentConfig


class SupportAgent:
    """支持代理 —— 使用知识库检索和工单创建工具处理员工咨询。"""

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self._retrieval = retrieval_service or RetrievalService()

    def search_knowledge_base(self, question: str, department: str | None = None, limit: int = 3) -> list[RetrievedChunk]:
        return self._retrieval.search(question, department=department, limit=limit)

    def _build_answer(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return ""
        lines = [f"[1] {chunks[0].content}"]
        for i, c in enumerate(chunks[1:], 2):
            lines.append(f"[{i}] {c.content}")
        return "\n\n".join(lines)

    def _persist_trace(self, trace_id: str, question: str, chunk_ids: str, answer: str, route: str, confidence: str, ticket_id: str | None, latency_ms: int) -> None:
        try:
            session = SessionLocal()
            trace = QueryTrace(
                id=trace_id,
                question=question,
                retrieved_chunk_ids=chunk_ids,
                answer=answer,
                route=route,
                confidence=confidence,
                ticket_id=ticket_id,
                latency_ms=latency_ms,
            )
            session.add(trace)
            session.commit()
        except (OSError, Exception) as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("Trace persist failed: %s", exc)
        finally:
            session.close()

    def _ticket_response(
        self,
        question: str,
        trace_id: str,
        chunk_ids: str,
        start: int,
        reason: str,
        risk_level: str,
    ) -> ChatResponse:
        """创建工单并持久化统一的低风险响应。"""
        ticket = ticket_service.create(question, reason=reason, risk_level=risk_level)
        latency_ms = int((time.monotonic_ns() - start) / 1_000_000)
        response = ChatResponse(
            answer="您的请求已转交技术支持团队处理，工单已创建。",
            citations=[],
            confidence="low",
            route="ticket",
            ticket_id=ticket.id,
            trace_id=trace_id,
            latency_ms=latency_ms,
        )
        self._persist_trace(
            trace_id,
            question,
            chunk_ids,
            response.answer,
            response.route,
            response.confidence,
            response.ticket_id,
            latency_ms,
        )
        return response

    def handle(self, question: str, department: str | None = None, config: "ExperimentConfig | None" = None) -> ChatResponse:
        # 每次请求都生成可追踪 ID，并从入口开始统计端到端延迟。
        trace_id = str(uuid.uuid4())
        start = time.monotonic_ns()

        top_k = config.retrieval.top_k if config else 3
        retrieval_mode = config.retrieval.mode if config else "vector"

        # 检索模式由 YAML 实验配置控制，便于比较向量、RRF 和三层精排的效果。
        if retrieval_mode in {"hybrid", "three_stage"}:
            chunks = self._retrieval.hybrid_search(
                question,
                department=department,
                limit=top_k,
                rerank=config.retrieval.rerank,
                rerank_top_n=config.retrieval.rerank_top_n,
            )
        else:
            chunks = self._retrieval.search(question, department=department, limit=top_k)

        # access filter (V3) — use authenticated user identity, not request department field
        if config is not None and config.grounding.access_filter:
            from app.support.grounding import (
                filter_by_access_level,
                resolve_access_level,
            )
            user_access = resolve_access_level(department)
            chunks = filter_by_access_level(chunks, user_access)

        # 路由同时考虑“是否有证据”和“是否是敏感操作”：任一不满足都不直接回答。
        evidence_count = len(chunks)
        route = decide_route(question, evidence_count)
        chunk_ids = ",".join(c.id for c in chunks)

        if route is Route.TICKET:
            # 工单是安全兜底，不执行密码重置、权限提升等真实系统操作。
            reason = "证据不足，或请求涉及敏感操作"
            risk_level = "high" if calculate_risk_score(question) > 0 else "low"
            return self._ticket_response(
                question,
                trace_id,
                chunk_ids,
                start,
                reason,
                risk_level,
            )

        # 回答与引用从同一批检索证据构造，保证页面展示的来源可追溯。
        citations = [
            Citation(chunk_id=c.id, title=c.title, excerpt=c.content[:200])
            for c in chunks
        ]
        answer = self._build_answer(chunks)

        # grounding check (V3)
        mandatory = config is not None and config.grounding.enabled and config.grounding.mandatory_citations
        if mandatory:
            from app.support.grounding import validate_grounding
            citation_ids = [c.chunk_id for c in citations]
            if not validate_grounding(answer, citation_ids):
                # 即使检索到了内容，只要回答无法被来源验证，仍降级到人工工单。
                return self._ticket_response(
                    question,
                    trace_id,
                    chunk_ids,
                    start,
                    "回答未通过来源验证",
                    "high",
                )

        try:
            answer = generate_answer(question, [chunk.content for chunk in chunks])
        except DeepSeekError:
            return self._ticket_response(
                question,
                trace_id,
                chunk_ids,
                start,
                "语言模型暂时不可用",
                "low",
            )

        if mandatory and not validate_grounding(answer, [c.chunk_id for c in citations]):
            return self._ticket_response(
                question,
                trace_id,
                chunk_ids,
                start,
                "回答未通过来源验证",
                "high",
            )

        latency_ms = int((time.monotonic_ns() - start) / 1_000_000)
        response = ChatResponse(
            answer=answer,
            citations=citations,
            confidence="high" if evidence_count >= 2 else "medium",
            route="answer",
            trace_id=trace_id,
            latency_ms=latency_ms,
        )
        # 成功回答也写入 Trace，便于审计、问题复盘和后续离线评估。
        self._persist_trace(trace_id, question, chunk_ids, response.answer, response.route, response.confidence, response.ticket_id, latency_ms)
        return response


support_agent = SupportAgent()
