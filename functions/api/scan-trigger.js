/**
 * DueSight — Scan Trigger (Cloudflare Pages Function)
 * =====================================================
 * POST /api/scan-trigger
 *
 * Accepts a scan request from the frontend, creates a scan record
 * and lead in Supabase, and returns the scan_id for status polling.
 *
 * Body: { domain, tier?, lead_name?, lead_email? }
 * Returns: { scan_id, status }
 */

async function supabasePost(env, table, data) {
  const resp = await fetch(`${env.SUPABASE_URL}/rest/v1/${table}`, {
    method: "POST",
    headers: {
      apikey: env.SUPABASE_SERVICE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify(data),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Supabase ${table} insert failed: ${resp.status} — ${text}`);
  }
  const rows = await resp.json();
  return rows[0] || null;
}

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: corsHeaders });
}

export async function onRequestPost(context) {
  const { request, env } = context;

  try {
    const body = await request.json();
    const { domain, tier = "quick_scan", lead_name, lead_email } = body;

    if (!domain || domain.trim().length < 2) {
      return Response.json({ error: "Domain is required" }, { status: 400, headers: corsHeaders });
    }

    const cleanDomain = domain
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\//, "")
      .replace(/^www\./, "")
      .replace(/\/+$/, "");

    // 1. Create scan record in Supabase
    const scan = await supabasePost(env, "scans", {
      domain: cleanDomain,
      company_name: cleanDomain.split(".")[0].charAt(0).toUpperCase() +
        cleanDomain.split(".")[0].slice(1),
      tier,
      status: "pending",
    });

    const scanId = scan?.id;
    if (!scanId) throw new Error("Failed to create scan record");

    // 2. Save lead if contact info provided (non-blocking)
    if (lead_name || lead_email) {
      await supabasePost(env, "leads", {
        scan_id: scanId,
        name: lead_name || null,
        email: lead_email || null,
        domain: cleanDomain,
        tier,
        source: "website",
      }).catch((err) => console.error("[scan-trigger] Lead save failed:", err.message));
    }

    // 3. Return scan_id for polling
    return Response.json(
      { scan_id: scanId, status: "pending", message: `Scan aangemaakt voor ${cleanDomain}` },
      { status: 201, headers: corsHeaders }
    );
  } catch (err) {
    console.error("[scan-trigger] Error:", err);
    return Response.json(
      { error: err.message || "Internal server error" },
      { status: 500, headers: corsHeaders }
    );
  }
}
