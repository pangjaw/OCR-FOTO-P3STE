import { NextRequest, NextResponse } from "next/server";
import { getPipelineState, runPipelineStep, stopPipeline } from "@/lib/pipeline-runner";

export async function GET() {
  const state = getPipelineState();
  return NextResponse.json(state);
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { step, detector } = body;
    if (!step) {
      return NextResponse.json({ error: "Parameter 'step' diperlukan" }, { status: 400 });
    }

    const result = await runPipelineStep(step, { detector });
    if (!result.success) {
      return NextResponse.json({ error: result.error }, { status: 400 });
    }

    return NextResponse.json({ success: true, step });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function DELETE() {
  const stopped = stopPipeline();
  return NextResponse.json({ success: stopped });
}
