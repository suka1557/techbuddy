def build_stt_cleanup_prompt(raw_text: str) -> str:
    """
    Creates a strict prompt for cleaning STT (Whisper) transcription
    of interview responses without adding new information.
    """

    prompt = f"""
        You are an assistant whose ONLY task is to clean and format a speech-to-text transcription.

        The transcription is from a candidate's interview response and may contain:
        - Misspelled words
        - Broken or incomplete sentences
        - Repeated phrases or duplicated chunks
        - Minor grammatical issues due to speech patterns

        Your job is to:

        1. Correct spelling mistakes
        2. Fix broken sentence structure where clearly intended
        3. Remove repeated or duplicate phrases
        4. Improve readability while preserving original meaning
        5. Keep the tone natural as spoken (do NOT make it overly formal)

        CRITICAL CONSTRAINTS (MUST FOLLOW):
        - DO NOT add any new information that is not present in the input
        - DO NOT infer or assume knowledge beyond what is spoken
        - DO NOT expand answers with explanations or examples
        - DO NOT complete thoughts that are unclear — keep them as-is if ambiguous
        - DO NOT change technical meaning
        - DO NOT summarize — preserve all original content (except duplicates)

        If a sentence is incomplete or unclear, retain it as closely as possible rather than guessing.

        Output requirements:
        - Return only the cleaned text
        - No explanations, no comments, no formatting notes
        - Keep it concise and faithful to the original speech

        ---

        RAW TRANSCRIPTION:
        \"\"\"
        {raw_text}
        \"\"\"

        CLEANED OUTPUT:
        """
    return prompt.strip()
