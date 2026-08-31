# OnLookout Product Spec

## Miner Response Schema (agent-friendly)
```json
{
  "location": {"lat": number, "lon": number, "name": string},
  "as_of": "ISO-8601 UTC",
  "forecast": [
    {
      "time": "ISO-8601",
      "temp_c": number,
      "precip_mm": number,
      "wind_ms": number,
      "conditions": string
    }
  ],
  "confidence": 0.0-1.0,
  "source": "open-meteo+fusion",
  "risk_flags": ["none" | "high_wind" | "heavy_precip" | "storm" | ...],
  "days": [
    {
      "date": "YYYY-MM-DD",
      "label": "today|tomorrow|date",
      "high_c": number,
      "low_c": number,
      "precip_mm": number,
      "condition": string
    }
  ],
  "summary": string,
  "answer": string,
  "canonical": string
}
```

Signal mapping for Telegraph: confidence_field=confidence, label_field=answer, reason_field=summary.
