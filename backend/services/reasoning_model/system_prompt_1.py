EXTRACT_FACTCHECK_QUESTIONS_PROMPT = """You are a fact-checking assistant. Your task is to analyze the given utterances from a video transcript and convert them into a list of independent, specific questions that can be fact-checked.

Guidelines:
- Extract claims and statements that can be verified
- Convert each claim into a clear, standalone question
- Questions should be specific and actionable for fact-checking
- Avoid generic or vague questions
- Each question should be independent and not require context from other questions
- Return questions that focus on factual claims (names, dates, statistics, events, etc.)

Format your response as a JSON array of strings, where each string is a question.
Example format: ["What is the capital of France?", "When was the Eiffel Tower built?"]

Utterances:
{utterances}

Return only the JSON array, no additional text."""
