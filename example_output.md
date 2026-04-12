{
  "status": "partial_success",
  "errors": [
    {
      "code": "LOW_CONFIDENCE",
      "message": "Speaker distinction unclear in parts of transcript",
      "severity": "warning",
      "details": {}
    }
  ],
  "meta": {
    "input_language": "Hindi",
    "confidence": 0.78,
    "notes": ""
  },
  "data": {
    "translated_text": "The government increased taxes last year. He says this is unfair.",
    "structured_dialogue": [
      {
        "speaker": "creator",
        "text": "The government increased taxes last year.",
        "confidence": 0.9
      },
      {
        "speaker": "other",
        "text": "This is unfair.",
        "confidence": 0.6
      }
    ],
    "claims_by_creator": [
      {
        "claim": "The government increased taxes last year",
        "type": "factual",
        "confidence": 0.88,
        "source_span": "The government increased taxes last year."
      }
    ]
  }
}
