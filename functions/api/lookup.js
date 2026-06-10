/**
 * DueSight — Company Lookup (Cloudflare Pages Function)
 * ======================================================
 * GET /api/lookup?q=<query>
 *
 * Searches Supabase companies cache first, falls back to Apollo API.
 * Returns company suggestions for the autocomplete dropdown.
 */

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

async function searchSupabase(env, query) {
  try {
    const resp = await fetch(
      `${env.SUPABASE_URL}/rest/v1/companies` +
        `?or=(company_name.ilike.*${encodeURIComponent(query)}*,domain.ilike.*${encodeURIComponent(query)}*)` +
        `&select=company_name,domain,sbi_description&limit=5`,
      {
        headers: {
          apikey: env.SUPABASE_SERVICE_KEY,
          Authorization: `Bearer ${env.SUPABASE_SERVICE_KEY}`,
        },
      }
    );
    if (!resp.ok) return [];
    const rows = await resp.json();
    return rows.map((r) => ({ name: r.company_name, domain: r.domain || "", industry: r.sbi_description || "" }));
  } catch { return []; }
}

async function searchApollo(env, query) {
  if (!env.APOLLO_API_KEY) return [];
  try {
    const resp = await fetch("https://api.apollo.io/api/v1/organizations/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: env.APOLLO_API_KEY, q_organization_name: query, per_page: 5 }),
    });
    if (!resp.ok) return [];
    const data = await resp.json();
    return (data.organizations || []).map((org) => ({
      name: org.name,
      domain: (org.website_url || "").replace(/^https?:\/\//, "").replace(/^www\./, "").replace(/\/+$/, ""),
      industry: org.industry || "",
    }));
  } catch { return []; }
}

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: corsHeaders });
}

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const query = (url.searchParams.get("q") || "").trim();

  if (query.length < 2) {
    return Response.json({ results: [] }, { headers: corsHeaders });
  }

  try {
    // Cache-first: check Supabase
    const cached = await searchSupabase(env, query);
    if (cached.length > 0) {
      return Response.json({ results: cached, source: "cache" }, { headers: corsHeaders });
    }

    // Fallback: Apollo API
    const apollo = await searchApollo(env, query);
    return Response.json(
      { results: apollo, source: apollo.length > 0 ? "apollo" : "none" },
      { headers: corsHeaders }
    );
  } catch (err) {
    return Response.json({ results: [], error: err.message }, { status: 500, headers: corsHeaders });
  }
}
