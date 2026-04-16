from typing import Dict, List

from services.analysis_service import AnalysisService
from services.document_service import DocumentService
from services.llm_service import LLMService


class ReportService:
    def __init__(self):
        self.document_service = DocumentService()
        self.analysis_service = AnalysisService()
        self.llm_service = LLMService()

    async def generate_report(
        self,
        doc_id: str,
        output_format: str = "obsidian",
        provider: str = "ollama",
        model_name: str = "qwen3:8b",
        target_language: str = "zh",
        user_prompt: str = None
    ) -> Dict:
        document = self.document_service.get_document(doc_id)
        if not document:
            raise ValueError("Document not found")

        analysis = await self.analysis_service.analyze_document(
            doc_id=doc_id,
            mode="translate_first",
            target_language=target_language,
            use_llm=True,
            provider=provider,
            user_prompt=user_prompt,
            model_name=model_name
        )

        title = analysis["title"]
        slide_outline = self._build_slide_outline(
            analysis=analysis,
            provider=provider,
            model_name=model_name
        )

        if output_format == "slides":
            content = self._build_slide_markdown(title, slide_outline)
        else:
            content = self._build_obsidian_note(title, analysis, slide_outline)

        return {
            "doc_id": doc_id,
            "output_format": output_format,
            "title": title,
            "content": content,
            "slide_outline": slide_outline,
            "metadata": {
                "risk_level": analysis["risk_level"],
                "target_language": target_language,
                "provider": provider,
                "model_name": model_name
            }
        }

    def _build_slide_outline(self, analysis: Dict, provider: str, model_name: str) -> List[Dict]:
        fallback = [
            {"title": "監測摘要", "bullets": [analysis["summary"]]},
            {"title": "風險判斷", "bullets": [f"風險等級：{analysis['risk_level']}"]},
            {"title": "關鍵證據", "bullets": analysis.get("evidence", [])[:3]},
            {"title": "建議行動", "bullets": self._build_action_items(analysis)}
        ]

        prompt = f"""
你是一位稅務顧問，請將以下分析內容整理成 4 頁簡報大綱。
每頁都要有 title 與 bullets。
只輸出 JSON：
{{
  "slides": [
    {{"title": "頁1", "bullets": ["重點1", "重點2"]}}
  ]
}}

分析內容：
標題：{analysis['title']}
風險等級：{analysis['risk_level']}
摘要：{analysis['summary']}
證據：{analysis.get('evidence', [])}
備註：{analysis.get('notes', [])}
"""
        data = self.llm_service.generate_json(
            prompt=prompt,
            schema_hint={"slides": fallback},
            provider=provider,
            model_name=model_name
        )
        slides = data.get("slides", fallback)
        normalized = []
        for slide in slides[:4]:
            title = slide.get("title") if isinstance(slide, dict) else None
            bullets = slide.get("bullets") if isinstance(slide, dict) else None
            normalized.append({
                "title": title or "未命名頁",
                "bullets": bullets or []
            })
        return normalized or fallback

    def _build_obsidian_note(self, title: str, analysis: Dict, slide_outline: List[Dict]) -> str:
        frontmatter = [
            "---",
            f"title: {title}",
            "tags:",
            "  - tax-monitor",
            f"  - risk-{analysis['risk_level'].lower()}",
            "---",
            ""
        ]
        body = [
            f"# {title}",
            "",
            "## 監測摘要",
            analysis["summary"],
            "",
            "## 自動關鍵字",
            ", ".join(analysis.get("auto_keywords", [])),
            "",
            "## 風險等級",
            analysis["risk_level"],
            "",
            "## 關鍵證據",
        ]
        body.extend(f"- {item}" for item in analysis.get("evidence", []))
        body.extend(["", "## 投影片大綱"])
        for slide in slide_outline:
            body.append(f"### {slide['title']}")
            body.extend(f"- {bullet}" for bullet in slide["bullets"])
        return "\n".join(frontmatter + body)

    def _build_slide_markdown(self, title: str, slide_outline: List[Dict]) -> str:
        lines = [f"# {title}", ""]
        for index, slide in enumerate(slide_outline, start=1):
            lines.append(f"## Slide {index}: {slide['title']}")
            lines.extend(f"- {bullet}" for bullet in slide["bullets"])
            lines.append("")
        return "\n".join(lines).strip()

    def _build_action_items(self, analysis: Dict) -> List[str]:
        if analysis["risk_level"] == "High":
            return ["立即檢視申報義務與生效日期", "安排稅務與法務共同評估", "建立後續追蹤提醒"]
        if analysis["risk_level"] == "Medium":
            return ["確認是否影響既有流程", "納入本月監控清單", "整理受影響部門"]
        return ["持續追蹤後續公告", "保留本次摘要供日後比對"]
