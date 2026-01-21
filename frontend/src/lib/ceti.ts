export type CETIResponse = {
  authorization: "GRANTED" | "DENIED"
  response_content: string | null
  scope?: any
  certification_id?: string
  refusal_diagnostics?: {
    failure_type: string
    details: string
    requirements_for_certification: string
  }
  meta?: Record<string, any>
}

export async function verifyWithCETI(
  query: string,
  riskTier: "LOW" | "MEDIUM" | "HIGH" = "MEDIUM"
): Promise<CETIResponse> {
  const res = await fetch("http://localhost:8000/verify", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, risk_tier: riskTier }),
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || "CETI gateway failure")
  }

  return res.json()
}
