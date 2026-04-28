# Style Compliance Checklist

After generating an article, verify each of these rules before presenting it to the user. Report pass/fail for each.

## Checks

### 1. NO_OXFORD_COMMA
Scan for patterns like ", and", ", or" that follow a list of three or more items. The Oxford comma must NOT be present.
- ❌ "Bitcoin, Ethereum, and Solana" → ✅ "Bitcoin, Ethereum and Solana"
- ❌ "sign up, deposit, and trade" → ✅ "sign up, deposit and trade"

### 2. SENTENCE_CASE_HEADINGS
All headings (##, ###, etc.) must use sentence case: capitalize only the first word and proper nouns.
- ❌ "## How To Get Started With Copy Trading" → ✅ "## How to get started with Copy Trading"
- Product names like "Copy Trading", "Bybit", "USDT" remain capitalized as proper nouns.

### 3. ACTIVE_VOICE
At least 90% of sentences should use active voice. Flag passive constructions.
- ❌ "The trade can be executed by clicking..." → ✅ "Click ... to execute the trade"
- ❌ "Rewards will be distributed by the team" → ✅ "The team will distribute rewards"
- Exception: T&C sections may use more passive voice — this is acceptable.

### 4. BANNED_WORDS
Check for words/phrases that the style guide prohibits:
- "utilize" → use "use"
- "leverage" (as verb meaning "use") → use "use"
- "in order to" → use "to"
- "commence" → use "start" or "begin"
- "prior to" → use "before"
- "subsequently" → use "then" or "after"
- "aforementioned" → use "this" or "the"
- "facilitate" → use "help" or "enable"
- "endeavor" → use "try"

### 5. NUMBER_FORMAT
- Numbers 1,000+ must have comma separators (1,000 not 1000)
- Spell out one through nine; use numerals for 10+
- Crypto amounts must include token symbol: "100 USDT" not "$100" (unless referencing fiat)
- Percentages: use the % symbol with no space: "12.5%" not "12.5 %"

### 6. DATE_FORMAT
- Follow Bybit house format: "Jul 29, 2024" (abbreviated month, day, comma, year)
- Always include timezone for campaign dates: "Jul 29, 2024, 10AM UTC"
- Never use DD/MM/YYYY or MM/DD/YYYY formats

### 7. META_DESCRIPTION
- Must be present at the start of the article
- Must be under 160 characters
- Must include the primary keyword (if one was provided)
- Must be descriptive and compelling (not just a repeat of the title)

### 8. CTA_PRESENT
- The article must end with a clear call to action
- Product Explainers: direct the reader to try the product
- Campaign Articles: direct the reader to join/participate
- The CTA should include a specific action, not just "learn more"

### 9. SCREENSHOT_SEQUENCE (Product Explainers only)
- At least 3 screenshot placeholders must be present (if screenshots were provided)
- Placeholders must appear in logical sequence matching the tutorial steps
- Each placeholder must have a descriptive caption
- Format: `[Screenshot: description]`

### 10. WORD_COUNT
- Product Explainers: 1,500–2,000 words (±15% tolerance = 1,275–2,300)
- Campaign Articles: 800–1,200 words (±15% tolerance = 680–1,380)
- Report the actual word count

### 11. HEADING_HIERARCHY
- Must start with a single H1 (#) for the title
- Sections use H2 (##)
- Sub-sections use H3 (###)
- Never skip levels (e.g., H1 → H3 without H2)

### 12. INCLUSIVE_LANGUAGE
- Use "they/their" for singular pronouns, never "he/she" or "his/her"
- Use "users" or "traders" rather than gendered terms
- Use "cryptocurrency" or "crypto" rather than slang

## Compliance Summary Format

```
---
**Compliance check:**
- Oxford comma: [✅/❌] [details if failed]
- Headings: [✅/❌] [details if failed]
- Active voice: [✅/❌] ~[X]%
- Banned words: [✅/❌] [list if found]
- Number formatting: [✅/❌] [details if failed]
- Date formatting: [✅/❌] [details if failed]
- Meta description: [✅/❌] [X] characters
- CTA: [✅/❌]
- Screenshots: [✅/❌/N/A] [count]
- Word count: [✅/❌] [actual] (target: [range])
- Heading hierarchy: [✅/❌]
- Inclusive language: [✅/❌]
```
