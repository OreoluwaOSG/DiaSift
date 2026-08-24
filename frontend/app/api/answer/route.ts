import { NextResponse } from "next/server";

const API_BASE_URL = process.env.DIASIFT_API_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  console.log("api base url here>>>", API_BASE_URL);
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { detail: "Request body must be valid JSON." },
      { status: 400 },
    );
  }

  try {
    const response = await fetch(`${API_BASE_URL}/answer`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Diasift API is not reachable. Start the FastAPI backend on http://127.0.0.1:8000.",
      },
      { status: 503 },
    );
  }
}
