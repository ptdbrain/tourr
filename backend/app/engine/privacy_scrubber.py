import re

def scrub_pii(text: str) -> str:
    """
    Remove Personally Identifiable Information (PII) from text.
    - Credit cards (13-16 digits with optional spaces/dashes)
    - Passports (Common formats: 1 letter + 7 digits, or 9 alphanumeric)
    - Email addresses
    """
    # 1. Credit Card (basic matching for 13-16 digit numbers, optionally separated by space or dash)
    cc_pattern = r'\b(?:\d[ -]*?){13,16}\b'
    text = re.sub(cc_pattern, '[REDACTED_CC]', text)

    # 2. Email Address
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    text = re.sub(email_pattern, '[REDACTED_EMAIL]', text)

    # 3. Passport Number (generic heuristic: 1-2 uppercase letters followed by 6-7 digits)
    passport_pattern = r'\b[A-Z]{1,2}[0-9]{6,7}\b'
    text = re.sub(passport_pattern, '[REDACTED_PASSPORT]', text)

    return text
