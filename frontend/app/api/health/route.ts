import { NextResponse } from "next/server";

const API_BASE_URL = process.env.DIASIFT_API_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      cache: "no-store",
    });
    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      {
        status: "offline",
        collection_name: "unknown",
        vectorstore_path: "unknown",
        indexed_chunks: null,
      },
      { status: 503 },
    );
  }
}
