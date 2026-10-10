import re
from typing import Tuple
from app.models.schemas import SafetyCheckResult


class AdultContentSafetyGuard:
    """
    Nexora Safety Layer: Blocks explicit sexually explicit/pornographic content
    while deliberately preserving and permitting legitimate educational, anatomical,
    and reproductive health inquiries.
    """

    # Indicators of explicit pornography / gratuitous sexually explicit content
    EXPLICIT_SEXUAL_PATTERNS = [
        r"\b(?:porn(?:ograph(?:y|ic))?|hardcore|erotic(?:a)?|cybersex|hentai|xx{1,2}|camgirl)\b",
        r"\b(?:blowjob|handjob|cumshot|gangbang|threesome|creampie|bukkake)\b",
        r"\b(?:write\s+erotica|generate\s+porn|write\s+a\s+sexual\s+story|nsfw\s+story)\b",
        r"\b(?:explicit\s+sex\s+scene|dirty\s+talk|erotic\s+roleplay)\b",
    ]

    # Explicit terms of severe harm (CSAM / non-consensual) - zero tolerance
    SEVERITY_HIGH_PATTERNS = [
        r"\b(?:underage|minor|child)\s+(?:porn|sexual|nude|nudity)\b",
        r"\b(?:non-consensual|rape|assault)\s+(?:erotica|story)\b",
    ]

    # Legitimate medical, anatomical, reproductive health, and educational context indicators
    EDUCATIONAL_MEDICAL_CONTEXT = [
        r"\b(?:biology|anatom(?:y|ical)|medical|health|clinical|patholog(?:y|ic))\b",
        r"\b(?:reproduct(?:ive|ion)|physiology|physician|doctor|diagnosis|treatment)\b",
        r"\b(?:puberty|fertil(?:ity|ization)|contracepti(?:on|ve)|pregnancy|obstetrics|gynecol(?:ogy|ogist))\b",
        r"\b(?:sti|std|infection|symptoms|prevention|transmission|testing)\b",
        r"\b(?:urolog(?:y|ist)|endocrinol(?:ogy|ogist)|pediatric|dermatolog(?:y|ist))\b",
        r"\b(?:textbook|academic|scientific|curriculum|education|research)\b",
    ]

    def evaluate_content(self, text: str) -> SafetyCheckResult:
        if not text:
            return SafetyCheckResult(is_safe=True, flagged=False)

        lower_text = text.lower()

        # Check for zero-tolerance severe abuse patterns first
        for pattern in self.SEVERITY_HIGH_PATTERNS:
            if re.search(pattern, lower_text):
                return SafetyCheckResult(
                    is_safe=False,
                    flagged=True,
                    category="child_safety_or_violence",
                    reason="Request contains severely harmful or non-consensual sexual content.",
                    educational_override=False,
                )

        # Check for educational or medical context
        is_educational = any(re.search(pat, lower_text) for pat in self.EDUCATIONAL_MEDICAL_CONTEXT)

        # Check for general sexually explicit patterns
        has_explicit_sexual = any(re.search(pat, lower_text) for pat in self.EXPLICIT_SEXUAL_PATTERNS)

        if has_explicit_sexual:
            if is_educational:
                # Educational or medical query about anatomy/health is permitted
                return SafetyCheckResult(
                    is_safe=True,
                    flagged=False,
                    category="medical_educational",
                    reason="Content contains sensitive anatomical/health keywords but was evaluated as legitimate medical or educational inquiry.",
                    educational_override=True,
                )
            else:
                return SafetyCheckResult(
                    is_safe=False,
                    flagged=True,
                    category="explicit_adult_content",
                    reason="Nexora AI safety policy prohibits the generation of explicit sexually gratuitous content, pornography, and erotica. Legitimate anatomical, biological, or medical inquiries are permitted.",
                    educational_override=False,
                )

        if is_educational:
            return SafetyCheckResult(
                is_safe=True,
                flagged=False,
                category="educational_inquiry",
                reason="Educational or scientific inquiry.",
                educational_override=True,
            )

        return SafetyCheckResult(is_safe=True, flagged=False)


safety_guard = AdultContentSafetyGuard()
