{
  "status": "success | partial_success | failure",

  "errors": [
    {
      "code": "TRANSLATION_ERROR | SPEAKER_DETECTION_ERROR | CLAIM_EXTRACTION_ERROR | LOW_CONFIDENCE | INVALID_INPUT",
      "message": "string",
      "severity": "warning | critical",
      "details": {}
    }
  ],

  "meta": {
    "input_language": "string",
    "confidence": 0.0,
    "notes": "string"
  },

  "data": {
    "translated_text": "string",

    "structured_dialogue": [
      {
        "speaker": "creator | other | unknown",
        "text": "string",
        "confidence": 0.0
      }
    ],

    "claims_by_creator": [
      {
        "claim": "string",
        "type": "factual | opinion | unclear",
        "confidence": 0.0,
        "source_span": "exact supporting text from dialogue"
      }
    ]
  }
}
