/**
 * DueSight — Scan Status (Cloudflare Pages Function)
 * ====================================================
 * GET /api/scan-status?id=<scan_id>
 *
 * Polls Supabase for current scan status.
 * Frontend calls this every 5s until status is 'completed' or 'failed'.
 */

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: corsHeaders });
}

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const scanId = url.searchParams.get("id");

  if (!scanId) {
    return Response.json({ error: "Missing scan id" }, { status: 400, headers: corsHeaders });
  }

  // UUID validation
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(scanId)) {
    return Response.json({ error: "Invalid scan id" }, { status: 400, headers: corsHeaders });
  }

  try {
    const fields = [
      "id", "domain", "company_name", "tier", "status",
      "risk_score", "risk_level", "confidence", "data_completeness",
      "execution_time_seconds", "total_cost_eur",
      "created_at", "completed_at", "error_message",
    ].join(",");

    const resp = await fetch(
      `${env.SUPABASE_URL}/rest/v1/scans?id=eq.${scanId}&select=${fields}`,
      {
        headers: {
          apikey: env.SUPABASE_ANON_KEY,
          Authorization: `Bearer ${env.SUPABASE_ANON_KEY}`,
        },
      }
    );

    if (!resp.ok) throw new Error(`Supabase query failed: ${resp.status}`);

    const rows = await resp.json();
    if (!rows?.length) {
      return Response.json({ error: "Scan not found" }, { status: 404, headers: corsHeaders });
    }

    const scan = rows[0];
    const result = {
      scan_id: scan.id,
      status: scan.status,
      domain: scan.domain,
      company_name: scan.company_name,
      tier: scan.tier,
      created_at: scan.created_at,
    };

    if (scan.status === "completed") {
      result.risk_score = scan.risk_score;
      result.risk_level = scan.risk_level;
      result.confidence = scan.confidence;
      result.data_completeness = scan.data_completeness;
      result.execution_time_seconds = scan.execution_time_seconds;
      result.completed_at = scan.completed_at;
    }

    if (scan.status === "failed" || scan.status === "aborted") {
      result.error_message = scan.error_message;
    }

    return Response.json(result, { headers: corsHeaders });
  } catch (err) {
    console.error("[scan-status] Error:", err);
    return Response.json(
      { error: err.message || "Internal server error" },
      { status: 500, headers: corsHeaders }
    );
  }
}
