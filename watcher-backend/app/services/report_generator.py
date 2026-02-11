"""
RPA - Report Generator

Automated report generation service for analysis results, trends, and insights.
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Report output formats"""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "markdown"
    CSV = "csv"


class ReportType(str, Enum):
    """Types of reports"""
    EXECUTIVE_SUMMARY = "executive_summary"
    DETAILED_ANALYSIS = "detailed_analysis"
    TREND_REPORT = "trend_report"
    ENTITY_REPORT = "entity_report"
    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_REPORT = "compliance_report"


class ReportGenerator:
    """
    Report Generator Service (RPA Layer).
    
    Responsibilities:
    - Generate executive summaries
    - Create detailed analysis reports
    - Produce trend and statistical reports
    - Format reports in multiple formats (JSON, HTML, PDF, MD)
    - Schedule automated report generation
    """
    
    def __init__(self):
        """Initialize report generator."""
        self.stats = {
            "reports_generated": 0,
            "by_type": {t.value: 0 for t in ReportType},
            "by_format": {f.value: 0 for f in ReportFormat},
            "errors": 0
        }
    
    async def generate_report(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        format: ReportFormat = ReportFormat.JSON,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a report.
        
        Args:
            report_type: Type of report to generate
            data: Data for the report
            format: Output format
            metadata: Optional metadata
            
        Returns:
            Generated report
        """
        try:
            logger.info(f"📊 Generating {report_type.value} report in {format.value} format")
            
            # Generate report based on type
            if report_type == ReportType.EXECUTIVE_SUMMARY:
                report_content = self._generate_executive_summary(data)
            elif report_type == ReportType.DETAILED_ANALYSIS:
                report_content = self._generate_detailed_analysis(data)
            elif report_type == ReportType.TREND_REPORT:
                report_content = self._generate_trend_report(data)
            elif report_type == ReportType.ENTITY_REPORT:
                report_content = self._generate_entity_report(data)
            elif report_type == ReportType.RISK_ASSESSMENT:
                report_content = self._generate_risk_assessment(data)
            else:
                report_content = {
                    "error": f"Report type {report_type.value} not implemented"
                }
            
            # Format report
            formatted_report = self._format_report(report_content, format)
            
            # Update stats
            self.stats["reports_generated"] += 1
            self.stats["by_type"][report_type.value] += 1
            self.stats["by_format"][format.value] += 1
            
            logger.info(f"✅ Report generated successfully")
            
            return {
                "success": True,
                "report_type": report_type.value,
                "format": format.value,
                "generated_at": datetime.now().isoformat(),
                "metadata": metadata or {},
                "content": formatted_report
            }
        
        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            self.stats["errors"] += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_executive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an executive summary report."""
        return {
            "title": "Executive Summary",
            "period": data.get("period", "Unknown"),
            "summary": {
                "total_documents": data.get("total_documents", 0),
                "high_risk_items": data.get("high_risk_count", 0),
                "total_amount": data.get("total_amount", 0),
                "key_findings": data.get("key_findings", [])
            },
            "highlights": [
                f"Processed {data.get('total_documents', 0)} documents",
                f"Identified {data.get('high_risk_count', 0)} high-risk items",
                f"Total financial impact: ${data.get('total_amount', 0):,.2f}"
            ],
            "recommendations": data.get("recommendations", [
                "Continue monitoring high-risk transactions",
                "Review flagged entities for compliance",
                "Update risk assessment criteria"
            ])
        }
    
    def _generate_detailed_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a detailed analysis report."""
        return {
            "title": "Detailed Analysis Report",
            "generated_at": datetime.now().isoformat(),
            "scope": data.get("scope", {}),
            "analysis": {
                "documents_analyzed": data.get("documents", []),
                "entities_identified": data.get("entities", {}),
                "risk_breakdown": data.get("risk_breakdown", {}),
                "patterns_detected": data.get("patterns", [])
            },
            "findings": data.get("findings", []),
            "detailed_items": data.get("detailed_items", [])
        }
    
    def _generate_trend_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a trend analysis report."""
        return {
            "title": "Trend Analysis Report",
            "period": data.get("period", "Unknown"),
            "trends": {
                "document_volume": data.get("document_trend", []),
                "risk_levels": data.get("risk_trend", []),
                "financial_trends": data.get("financial_trend", []),
                "entity_activity": data.get("entity_trend", [])
            },
            "insights": [
                "Document volume increased by X%",
                "High-risk detections trending upward",
                "New entities appearing in recent period"
            ],
            "projections": data.get("projections", {})
        }
    
    def _generate_entity_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an entity-focused report."""
        return {
            "title": "Entity Report",
            "entity_name": data.get("entity_name", "Unknown"),
            "entity_type": data.get("entity_type", "Unknown"),
            "profile": {
                "first_appearance": data.get("first_seen", "Unknown"),
                "total_mentions": data.get("mention_count", 0),
                "total_contracts": data.get("contract_count", 0),
                "total_amount": data.get("total_amount", 0)
            },
            "activity_timeline": data.get("timeline", []),
            "related_entities": data.get("related_entities", []),
            "risk_indicators": data.get("risk_indicators", [])
        }
    
    def _generate_risk_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a risk assessment report."""
        return {
            "title": "Risk Assessment Report",
            "assessment_date": datetime.now().isoformat(),
            "overall_risk_level": data.get("overall_risk", "MEDIUM"),
            "risk_breakdown": {
                "high": data.get("high_risk_count", 0),
                "medium": data.get("medium_risk_count", 0),
                "low": data.get("low_risk_count", 0)
            },
            "risk_factors": data.get("risk_factors", []),
            "high_risk_items": data.get("high_risk_items", []),
            "mitigation_recommendations": [
                "Implement additional controls for high-risk transactions",
                "Enhance monitoring of flagged entities",
                "Review and update risk thresholds"
            ]
        }
    
    def _format_report(self, content: Dict[str, Any], format: ReportFormat) -> Any:
        """Format report in specified format."""
        if format == ReportFormat.JSON:
            return content
        
        elif format == ReportFormat.MARKDOWN:
            return self._to_markdown(content)
        
        elif format == ReportFormat.HTML:
            return self._to_html(content)
        
        elif format == ReportFormat.CSV:
            return self._to_csv(content)
        
        elif format == ReportFormat.PDF:
            # PDF generation would require additional libraries
            return {
                "error": "PDF generation not yet implemented",
                "json_content": content
            }
        
        return content
    
    def _to_markdown(self, content: Dict[str, Any]) -> str:
        """Convert report to Markdown format."""
        md_lines = []
        
        # Title
        if "title" in content:
            md_lines.append(f"# {content['title']}\n")
        
        # Generated date
        if "generated_at" in content:
            md_lines.append(f"**Generated:** {content['generated_at']}\n")
        
        # Summary section
        if "summary" in content:
            md_lines.append("## Summary\n")
            for key, value in content["summary"].items():
                md_lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
            md_lines.append("")
        
        # Highlights
        if "highlights" in content:
            md_lines.append("## Key Highlights\n")
            for highlight in content["highlights"]:
                md_lines.append(f"- {highlight}")
            md_lines.append("")
        
        # Recommendations
        if "recommendations" in content:
            md_lines.append("## Recommendations\n")
            for i, rec in enumerate(content["recommendations"], 1):
                md_lines.append(f"{i}. {rec}")
            md_lines.append("")
        
        return "\n".join(md_lines)
    
    def _to_html(self, content: Dict[str, Any]) -> str:
        """Convert report to HTML format."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{content.get('title', 'Report')}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 40px; }",
            "h1 { color: #333; }",
            "h2 { color: #666; margin-top: 30px; }",
            ".summary { background: #f5f5f5; padding: 20px; border-radius: 5px; }",
            "ul { line-height: 1.8; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{content.get('title', 'Report')}</h1>",
        ]
        
        if "generated_at" in content:
            html_parts.append(f"<p><strong>Generated:</strong> {content['generated_at']}</p>")
        
        if "summary" in content:
            html_parts.append("<div class='summary'>")
            html_parts.append("<h2>Summary</h2>")
            html_parts.append("<ul>")
            for key, value in content["summary"].items():
                html_parts.append(f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>")
            html_parts.append("</ul>")
            html_parts.append("</div>")
        
        if "highlights" in content:
            html_parts.append("<h2>Key Highlights</h2>")
            html_parts.append("<ul>")
            for highlight in content["highlights"]:
                html_parts.append(f"<li>{highlight}</li>")
            html_parts.append("</ul>")
        
        html_parts.extend(["</body>", "</html>"])
        
        return "\n".join(html_parts)
    
    def _to_csv(self, content: Dict[str, Any]) -> str:
        """Convert report to CSV format (simplified)."""
        csv_lines = []
        
        # Header
        csv_lines.append("Report Type,Field,Value")
        
        # Flatten content
        report_type = content.get("title", "Unknown")
        
        for key, value in content.items():
            if isinstance(value, (str, int, float)):
                csv_lines.append(f"{report_type},{key},{value}")
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    csv_lines.append(f"{report_type},{key}.{sub_key},{sub_value}")
        
        return "\n".join(csv_lines)
    
    async def generate_batch_reports(
        self,
        reports: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple reports in batch.
        
        Args:
            reports: List of report specifications
            
        Returns:
            List of generated reports
        """
        results = []
        
        for report_spec in reports:
            result = await self.generate_report(
                report_type=ReportType(report_spec.get("type", "executive_summary")),
                data=report_spec.get("data", {}),
                format=ReportFormat(report_spec.get("format", "json")),
                metadata=report_spec.get("metadata")
            )
            results.append(result)
        
        logger.info(f"📊 Generated {len(results)} reports in batch")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "reports_generated": 0,
            "by_type": {t.value: 0 for t in ReportType},
            "by_format": {f.value: 0 for f in ReportFormat},
            "errors": 0
        }


# Global instance
_report_generator: Optional[ReportGenerator] = None


def get_report_generator() -> ReportGenerator:
    """Get or create global report generator instance."""
    global _report_generator
    
    if _report_generator is None:
        _report_generator = ReportGenerator()
    
    return _report_generator
