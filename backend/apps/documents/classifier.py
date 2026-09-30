import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple
from .models import DocumentClassificationType


@dataclass
class ClassificationOutcome:
    predicted_type: str
    confidence: float
    classifier_version: str
    classification_method: str
    evidence_summary: Dict[str, Any] = field(default_factory=dict)


class DocumentClassifier:
    """
    Deterministic rule-based document classification engine.
    Analyzes extracted text, headers, and keyword frequencies.
    Does not pretend to be ML: explicitly returns UNKNOWN when evidence is ambiguous.
    """

    VERSION = "1.0.0"

    RULES = [
        (
            DocumentClassificationType.INCOME_CERTIFICATE,
            [
                r'\bincome\s+certificate\b',
                r'\bannual\s+(?:family\s+)?income\b',
                r'\btahasildar\b',
                r'\brevenue\s+(?:department|officer|inspector)\b',
                r'\baay\s+praman\s+patra\b',
                r'\btaluk\s+office\b',
                r'\bsub-divisional\s+magistrate\b',
                r'\bcompetent\s+authority\b.*?\bincome\b',
                r'\bgross\s+annual\s+income\b',
            ],
            2.0  # Weight multiplier
        ),
        (
            DocumentClassificationType.CASTE_CERTIFICATE,
            [
                r'\bcaste\s+certificate\b',
                r'\bscheduled\s+tribe\b',
                r'\bcommunity\s+certificate\b',
                r'\btribe\s+certificate\b',
                r'\bjati\s+praman\s+patra\b',
                r'\barticle\s+342\b',
                r'\bconstitution\s+\(scheduled\s+tribes\)\b',
                r'\bst\s+certificate\b',
            ],
            2.5
        ),
        (
            DocumentClassificationType.DOMICILE_CERTIFICATE,
            [
                r'\bdomicile\s+certificate\b',
                r'\bresidence\s+certificate\b',
                r'\bpermanent\s+resident\b',
                r'\bniwas\s+praman\s+patra\b',
                r'\bresident\s+of\b',
                r'\bbonafide\s+resident\b',
            ],
            2.0
        ),
        (
            DocumentClassificationType.MARKSHEET,
            [
                r'\bmarksheet\b',
                r'\bstatement\s+of\s+marks\b',
                r'\bgrade\s+card\b',
                r'\bacademic\s+transcript\b',
                r'\bsemester\b',
                r'\bcgpa\b',
                r'\bsgpa\b',
                r'\bpercentage\b',
                r'\bexamination\s+results?\b',
                r'\btotal\s+marks\b',
            ],
            2.0
        ),
        (
            DocumentClassificationType.ADMISSION_LETTER,
            [
                r'\badmission\s+letter\b',
                r'\boffer\s+of\s+admission\b',
                r'\bprovisional\s+admission\b',
                r'\benrolment\s+letter\b',
                r'\ballotment\s+letter\b',
                r'\bcongratulations.*?\badmitted\b',
                r'\bfee\s+structure\b',
            ],
            2.0
        ),
        (
            DocumentClassificationType.INSTITUTION_DOCUMENT,
            [
                r'\bbonafide\s+certificate\b',
                r'\binstitution\s+verification\b',
                r'\bhead\s+of\s+institution\b',
                r'\bcollege\s+seal\b',
                r'\bprincipal\b',
                r'\bregistrar\b',
            ],
            1.8
        ),
        (
            DocumentClassificationType.BANK_DOCUMENT,
            [
                r'\bbank\s+passbook\b',
                r'\baccount\s+statement\b',
                r'\bifsc\s+code\b',
                r'\baccount\s+number\b',
                r'\bbranch\s+name\b',
                r'\bsavings\s+account\b',
                r'\bmicr\b',
            ],
            2.2
        ),
        (
            DocumentClassificationType.IDENTITY_DOCUMENT,
            [
                r'\belection\s+commission\s+of\s+india\b',
                r'\bvoter\s+id\b',
                r'\belector\s+photo\s+identity\b',
                r'\bpassport\b',
                r'\brepublic\s+of\s+india\b',
                r'\bdriving\s+licence\b',
                r'\baadhaar\b',
                r'\bunique\s+identification\s+authority\b',
            ],
            2.2
        ),
    ]

    @classmethod
    def classify(cls, full_text: str) -> ClassificationOutcome:
        """
        Evaluates full extracted text against canonical category rule patterns.
        """
        if not full_text or len(full_text.strip()) < 10:
            return ClassificationOutcome(
                predicted_type=DocumentClassificationType.UNKNOWN,
                confidence=0.0,
                classifier_version=cls.VERSION,
                classification_method="RULE_BASED",
                evidence_summary={"reason": "Text payload is empty or too short (< 10 chars)."}
            )

        text_lower = full_text.lower()
        scores: Dict[str, float] = {}
        matches_found: Dict[str, List[str]] = {}

        for doc_type, patterns, weight in cls.RULES:
            matched_patterns = []
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    matched_patterns.append(pattern)

            if matched_patterns:
                # Score formula: number of unique matches * weight
                score = len(matched_patterns) * weight
                scores[doc_type] = score
                matches_found[doc_type] = matched_patterns

        if not scores:
            return ClassificationOutcome(
                predicted_type=DocumentClassificationType.UNKNOWN,
                confidence=0.0,
                classifier_version=cls.VERSION,
                classification_method="RULE_BASED",
                evidence_summary={"reason": "No categorical keywords matched text."}
            )

        # Sort descending by score
        sorted_types = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_type, top_score = sorted_types[0]

        # Calculate normalized confidence
        # 1 match with weight 2.0 = ~0.6, 2+ matches = 0.85 - 0.99
        raw_conf = min(0.99, (top_score / 6.0) + 0.4) if top_score >= 2.0 else (top_score / 5.0)

        # If runner up is very close, reduce confidence
        if len(sorted_types) > 1:
            runner_up_type, runner_up_score = sorted_types[1]
            if top_score - runner_up_score < 1.0:
                raw_conf = raw_conf * 0.7  # Ambiguity penalty

        confidence = round(raw_conf, 2)

        # Below 0.40 confidence threshold -> mark as UNKNOWN rather than guessing
        if confidence < 0.40:
            return ClassificationOutcome(
                predicted_type=DocumentClassificationType.UNKNOWN,
                confidence=confidence,
                classifier_version=cls.VERSION,
                classification_method="RULE_BASED",
                evidence_summary={
                    "low_confidence_matches": matches_found,
                    "top_candidate": top_type,
                    "reason": "Confidence below threshold (0.40)."
                }
            )

        return ClassificationOutcome(
            predicted_type=top_type,
            confidence=confidence,
            classifier_version=cls.VERSION,
            classification_method="RULE_BASED",
            evidence_summary={
                "matched_patterns": matches_found[top_type],
                "score": top_score,
                "all_candidates": {k: round(v, 2) for k, v in scores.items()}
            }
        )
