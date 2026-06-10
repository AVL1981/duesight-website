"""
DueSight Contract Triage — Pre-DD Red Flag Scanner v1.0
=========================================================

⚠️  POSITIONERINGS-DISCLAIMER (NIET VERWIJDEREN):
Dit is GEEN contract review tool. DueSight doet GEEN clause-level analyse
(Harvey/Luminance/Kira/Spellbook territory). Deze module is uitsluitend
bedoeld als pre-DD **triage**: detecteert rode vlaggen op basis van regex
patterns zodat de M&A-advocaat weet WÁÁR hij/zij moet kijken.

Wat deze module WEL doet:
  - PDF/DOCX text extractie (pdfplumber, python-docx)
  - Regex-based red flag detectie (30+ patronen, EN/NL/DE)
  - Gestructureerde JSON output: gevonden flags + locatie (page) + severity
  - Source citation (page-level, byte-exact text)

Wat deze module NIET doet:
  - Clausule-extractie of -samenvatting
  - Legal advice of contract review
  - Partij-identificatie of datums
  - Volledige tekst-matching (alleen flagged phrases)

Bron limitaties:
  - PDF parsing kan falen op gescande PDFs (image-only)
  - DOCX parsing vereist python-docx
  - Max 50 pagina's per keer (grote contracten moeten chunked)

Cost: €0 (pure Python regex, geen LLM, geen API calls)
Speed: <5 seconden voor 50-pagina contract
Wire in: scan_server.py /api/contract/triage endpoint

Positioning: "DueSight herkent risico-patronen in contracten, geen legal review"
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger("duesight.contract_triage")


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Severity enum — strikt voor rode vlaggen
class FlagSeverity(str, Enum):
    CRITICAL = "CRITICAL"   # M&A-deal-breker, direct stoppen
    HIGH = "HIGH"           # Materieel, nader onderzoek vereist
    MEDIUM = "MEDIUM"       # Aandachtspunt, due diligence
    LOW = "LOW"             # Noted, geen actie

# Disclaimer constant — GEEN marketing zonder deze tekst
TRIAGE_DISCLAIMER = (
    "Dit is een geautomatiseerde pre-DD triage op basis van regex-patronen. "
    "GEEN legal advice, GEEN clause review, GEEN vervanging voor M&A-advocaat. "
    "Gevonden flags vereisen handmatige verificatie door juridisch expert."
)


# ═══════════════════════════════════════════════════════════════════════════════
# RED FLAG PATTERN LIBRARY (30+ patronen, EN/NL/DE)
# ═══════════════════════════════════════════════════════════════════════════════

RED_FLAG_PATTERNS: Dict[str, Dict[str, Any]] = {
    # ── LIABILITY & INDEMNIFICATION ────────────────────────────────────────
    "UNLIMITED_LIABILITY": {
        "severity": FlagSeverity.CRITICAL,
        "patterns": [
            r"(?i)\bunlimited\s+liability\b",
            r"(?i)\bonbeperkte\s+aansprakelijkheid\b",
            r"(?i)\bunbeschränkte\s+haftung\b",
        ],
        "description": "Onbeperkte aansprakelijkheid — Materieel risico voor koper",
    },
    "INDEMNIFICATION_BROAD": {
        "severity": FlagSeverity.HIGH,
        "patterns": [
            r"(?i)\bindemnif(?:y|ication|ies)\b.*?\b(all|any|every)\b",
            r"(?i)\bvrijwaring\b.*?\b(alle|elke)\b",
            r"(?i)\bfreistellung\b.*?\b(alle|jede)\b",
        ],
        "description": "Brede vrijwaringsverplichting zonder cap",
    },
    "LIQUIDATED_DAMAGES_EXCESSIVE": {
        "severity": FlagSeverity.HIGH,
        "patterns": [
            r"(?i)\bliquidated\s+damages\b.*?(?:excessive|unlimited|no cap)",
            r"(?i)\bfixed\s+damages\b.*?(\d{2,}\s*%)",
        ],
        "description": "Excessieve gefixeerde schadevergoeding",
    },
    # ── M&A SPECIFIC (CHANGE OF CONTROL, MAC) ─────────────────────────────
    "CHANGE_OF_CONTROL_NO_NOTICE": {
        "severity": FlagSeverity.CRITICAL,
        "patterns": [
            # EN: change of control ... without ... notice (max 5 woorden tussen without en notice)
            r"(?i)change\s+of\s+control(?:\s+\w+){0,8}\s+without(?:\s+\w+){0,4}\s+(?:prior\s+)?notice",
            # NL: wijziging van controle ... zonder ... kennisgeving
            r"(?i)wijziging\s+van\s+controle(?:\s+\w+){0,8}\s+zonder(?:\s+\w+){0,4}\s+(?:voorafgaande\s+)?kennisgeving",
            # DE: Kontrollwechsel ... ohne ... Ankündigung
            r"(?i)kontrollwechsel(?:\s+\w+){0,8}\s+ohne(?:\s+\w+){0,4}\s+(?:vorherige\s+)?ankündigung",
        ],
        "description": "Change of control zonder voorafgaande kennisgeving — direct impact bij M&A",
    },
    "MAC_CLAUSE_BROAD": {
        "severity": FlagSeverity.HIGH,
        "patterns": [
            r"(?i)material\s+adverse\s+change.*?(?:any|all|every)",
            r"(?i)materiaal\s+nadelig\s+effect.*?(?:alle|elke)",
            r"(?i)wesentliche\s+nachteilige\s+veränderung.*?(?:alle|jede)",
        ],
        "description": "Te brede Material Adverse Change definitie — kan exit-recht voor koper ondermijnen",
    },
    # ── JURISDICTION & GOVERNING LAW ───────────────────────────────────────
    "GOVERNING_LAW_OFFSHORE": {
        "severity": FlagSeverity.HIGH,
        "patterns": [
            r"(?i)governed\s+by.*?(delaware|cayman|bvi|curacao|cyprus)",
            r"(?i)toepasselijk\s+recht.*?(delaware|cayman|bvi|curacao|cyprus)",
            r"(?i)anwendbares\s+recht.*?(delaware|cayman|bvi|curacao|zypern)",
        ],
        "description": "Offshore governing law — verhoogt handhavingsrisico",
    },
    "ARBITRATION_MANDATORY": {
        "severity": FlagSeverity.MEDIUM,
        "patterns": [
            r"(?i)\bmandatory\s+arbitration\b",
            r"(?i)\bverplichte\s+arbitrage\b",
            r"(?i)\bverpflichtende\s+schiedsgerichtsbarkeit\b",
        ],
        "description": "Verplichte arbitrage — kan geschilbeslechting duurder maken",
    },
    # ── NON-COMPETE & RESTRICTIVE COVENANTS ───────────────────────────────
    "NON_COMPETE_DURATION_LONG": {
        "severity": FlagSeverity.HIGH,
        "patterns": [
            r"(?i)non[\s-]?compete.*?(\d+)\s*year",
            r"(?i)niet[\s-]?concurrentie.*?(\d+)\s*jaar",
            r"(?i)wettbewerbsverbot.*?(\d+)\s*jahr",
        ],
        "description": "Non-compete duur > 2 jaar — vergt nader onderzoek",
    },
    "NON_COMPETE_GEOGRAPHY_BROAD": {
        "severity": FlagSeverity.HIGH,
        "patterns": [
            r"(?i)non[\s-]?compete.*?(worldwide|global|entire\s+(?:world|europe))",
            r"(?i)niet[\s-]?concurrentie.*?(wereldwijd|globaal|hele\s+(?:wereld|Europa))",
        ],
        "description": "Non-compete geografisch te breed",
    },
    "NON_SOLICIT_OVERREACHING": {
        "severity": FlagSeverity.MEDIUM,
        "patterns": [
            r"(?i)non[\s-]?solicit.*?(all|any|every)\s+(?:customer|employee|client)",
            r"(?i)geen\s+werfkorting.*?(alle|elke)",
        ],
        "description": "Non-solicit te breed — kan post-M&A exit belemmeren",
    },
    # ── IP & DATA ─────────────────────────────────────────────────────────
    "IP_ASSIGNMENT_BROAD": {
        "severity": FlagSeverity.HIGH,
        "patterns": [
            r"(?i)assign(?:s|ment)?\s+all\s+(?:right|title|interest).*?(?:intellectual|IP|invention)",
            r"(?i)\boverdraagt\s+alle\b.*?(?:intellectuele|IE|uitvinding)",
        ],
        "description": "IP-overdracht zonder voorbehoud — verlies van IP-rechten",
    },
    "DATA_PROTECTION_INADEQUATE": {
        "severity": FlagSeverity.HIGH,
        "patterns": [
            r"(?i)(?:gdpr|avg).*?(?:waive|opt[\s-]?out|niet\s+noodzakelijk)",
            r"(?i)(?:data\s+protection).*?(?:waive|opt[\s-]?out)",
        ],
        "description": "GDPR/AVG waiver — ongeldig onder EU recht, compliance risico",
    },
    "CONFIDENTIALITY_OVERREACHING": {
        "severity": FlagSeverity.MEDIUM,
        "patterns": [
            r"(?i)perpetual\s+confidentiality",
            r"(?i)\bperpetueel\b.*?(?:vertrouwelijk|geheim)",
            r"(?i)ewige\s+geheimhaltung",
        ],
        "description": "Perpetueel confidentiality — kan post-deal hinderen",
    },
    # ── ESCROW & PAYMENT ──────────────────────────────────────────────────
    "ESCROW_TERMS_UNFAIR": {
        "severity": FlagSeverity.HIGH,
        "patterns": [
            r"(?i)escrow.*?(?:never\s+release|unlimited\s+hold|no\s+release)",
            r"(?i)\bescrow\b.*?(?:nooit\s+vrijgegeven|onbeperkt)",
        ],
        "description": "Escrow met onmogelijke vrijgave — koopprijs risico",
    },
    # ── AUTO-RENEWAL & TERMINATION ────────────────────────────────────────
    "AUTO_RENEWAL_NO_NOTICE": {
        "severity": FlagSeverity.MEDIUM,
        "patterns": [
            r"(?i)automatic\s+renewal.*?(?:unless.*?notice|geen\s+opzegging)",
            r"(?i)\bautomatische\s+verlenging\b.*?(?:zonder|geen)",
        ],
        "description": "Auto-renewal zonder opzegmogelijkheid",
    },
    "TERMINATION_WITHOUT_CAUSE": {
        "severity": FlagSeverity.MEDIUM,
        "patterns": [
            r"(?i)terminate\s+at\s+will\s+without\s+cause",
            r"(?i)opzeggen\s+zonder\s+reden",
        ],
        "description": "Termination at will — onmiddellijke beëindiging mogelijk",
    },
    # ── WARRANTY & DISCLAIMER ─────────────────────────────────────────────
    "WARRANTY_DISCLAIMER_BROAD": {
        "severity": FlagSeverity.MEDIUM,
        "patterns": [
            r"(?i)disclaim(?:s|er)?\s+all\s+warrant(?:y|ies)",
            r"(?i)\bsluit\s+alle\s+garanties\s+uit\b",
        ],
        "description": "Brede warranty disclaimer — koper weet weinig over product",
    },
    "FORCE_MAJEURE_BROAD": {
        "severity": FlagSeverity.LOW,
        "patterns": [
            r"(?i)force\s+majeure.*?(?:any|all|every)\s+(?:event|circumstance)",
            r"(?i)\bovermacht\b.*?(?:alle|elke|iedere)\s+(?:gebeurtenis|omstandigheid)",
        ],
        "description": "Force majeure te breed — kan performance-uitval legitimeren",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RedFlag:
    """Een gevonden rode vlag in een contract."""
    flag_type: str
    severity: str  # CRITICAL / HIGH / MEDIUM / LOW
    description: str
    matched_text: str  # Exacte tekst die de flag triggerde
    page_number: Optional[int] = None  # Page-level citation
    char_offset: Optional[int] = None  # Positie in text
    line_number: Optional[int] = None  # Line in text
    confidence: float = 1.0  # Deterministic regex = altijd 1.0


@dataclass
class TriageResult:
    """Gestructureerd triage-resultaat voor pre-DD screening."""
    company_name: str  # Optioneel, bij target context
    source_file: str  # Bestandsnaam of identifier
    source_pages: int = 0
    flags: List[RedFlag] = field(default_factory=list)
    flagged_count_by_severity: Dict[str, int] = field(default_factory=dict)
    risk_score: int = 0  # 0-100
    risk_level: str = "UNKNOWN"  # LOW / MEDIUM / HIGH / CRITICAL
    disclaimer: str = TRIAGE_DISCLAIMER
    scan_timestamp: str = field(default_factory=lambda: str(__import__('datetime').datetime.now().isoformat()))

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "source_file": self.source_file,
            "source_pages": self.source_pages,
            "flags": [asdict(f) for f in self.flags],
            "flagged_count_by_severity": self.flagged_count_by_severity,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "disclaimer": self.disclaimer,
            "scan_timestamp": self.scan_timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONTRACT TRIAGE SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

class ContractTriageScanner:
    """
    Pre-DD contract triage scanner (regex-based red flag detection).

    ⚠️  NIET voor clause-extractie, NIET legal review, NIET legal advice.
    Zie TRIAGE_DISCLAIMER constant.
    """

    # Max pagina's (PDF) of chunk size (DOCX) per keer
    MAX_PAGES = 50

    def __init__(self, company_name: str = ""):
        self.company_name = company_name
        # Compile regex patterns eenmalig
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {
            flag_type: [re.compile(p) for p in info["patterns"]]
            for flag_type, info in RED_FLAG_PATTERNS.items()
        }

    async def triage_pdf(self, pdf_path: str) -> TriageResult:
        """
        Triage een PDF contract.

        Vereist: pdfplumber (pip install pdfplumber)
        Fallback: lege resultaat + warning als pdfplumber niet beschikbaar
        """
        result = TriageResult(
            company_name=self.company_name,
            source_file=os.path.basename(pdf_path),
        )
        try:
            import pdfplumber
        except ImportError:
            logger.warning("[ContractTriage] pdfplumber niet beschikbaar — install: pip install pdfplumber")
            result.risk_level = "UNKNOWN"
            return result

        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages = pdf.pages[:self.MAX_PAGES]
                result.source_pages = len(pages)
                for page_num, page in enumerate(pages, start=1):
                    text = page.extract_text() or ""
                    self._scan_text(text, page_num, result)
        except Exception as e:
            logger.warning(f"[ContractTriage] PDF parse error: {e}")

        self._finalize(result)
        return result

    async def triage_text(self, text: str, source_label: str = "raw_text") -> TriageResult:
        """
        Triage rauwe tekst (voor DOCX-na-text conversie of al geëxtraheerde content).
        """
        result = TriageResult(
            company_name=self.company_name,
            source_file=source_label,
            source_pages=1,
        )
        self._scan_text(text, page_number=1, result=result)
        self._finalize(result)
        return result

    async def triage_docx(self, docx_path: str) -> TriageResult:
        """
        Triage een DOCX contract.

        Vereist: python-docx (pip install python-docx)
        """
        result = TriageResult(
            company_name=self.company_name,
            source_file=os.path.basename(docx_path),
        )
        try:
            from docx import Document
        except ImportError:
            logger.warning("[ContractTriage] python-docx niet beschikbaar — install: pip install python-docx")
            return result

        try:
            doc = Document(docx_path)
            text = "\n".join([p.text for p in doc.paragraphs])
            result.source_pages = 1
            self._scan_text(text, page_number=1, result=result)
        except Exception as e:
            logger.warning(f"[ContractTriage] DOCX parse error: {e}")

        self._finalize(result)
        return result

    def _scan_text(self, text: str, page_number: int, result: TriageResult) -> None:
        """Scan tekst voor alle red flag patterns."""
        for flag_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    matched = match.group(0)
                    line_num = text[:match.start()].count('\n') + 1
                    result.flags.append(RedFlag(
                        flag_type=flag_type,
                        severity=RED_FLAG_PATTERNS[flag_type]["severity"].value,
                        description=RED_FLAG_PATTERNS[flag_type]["description"],
                        matched_text=matched[:200],  # truncate voor memory safety
                        page_number=page_number,
                        char_offset=match.start(),
                        line_number=line_num,
                        confidence=1.0,  # regex match = deterministic
                    ))

    def _finalize(self, result: TriageResult) -> None:
        """Aggregate flags naar risk score + level."""
        # Count by severity
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for flag in result.flags:
            counts[flag.severity] = counts.get(flag.severity, 0) + 1
        result.flagged_count_by_severity = counts

        # Risk score berekening
        score = 0
        score += counts["CRITICAL"] * 30
        score += counts["HIGH"] * 15
        score += counts["MEDIUM"] * 5
        score += counts["LOW"] * 1
        result.risk_score = min(100, score)

        # Risk level
        if counts["CRITICAL"] > 0:
            result.risk_level = "CRITICAL"
        elif counts["HIGH"] >= 2:
            result.risk_level = "HIGH"
        elif counts["HIGH"] >= 1 or counts["MEDIUM"] >= 3:
            result.risk_level = "MEDIUM"
        elif counts["MEDIUM"] > 0 or counts["LOW"] > 0:
            result.risk_level = "LOW"
        else:
            result.risk_level = "CLEAN"


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "ContractTriageScanner",
    "TriageResult",
    "RedFlag",
    "FlagSeverity",
    "RED_FLAG_PATTERNS",
    "TRIAGE_DISCLAIMER",
]
