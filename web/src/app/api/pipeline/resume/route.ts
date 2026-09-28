import { NextRequest, NextResponse } from "next/server";
import { resumePipeline } from "@/lib/pipeline-runner";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action } = body;
    if (!action || (action !== "continue_guide" && action !== "stop")) {
      return NextResponse.json(
        { error: "Parameter 'action' harus 'continue_guide' atau 'stop'" },
        { status: 400 }
      );
    }

    const success = resumePipeline(action);
    return NextResponse.json({ success, action });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
