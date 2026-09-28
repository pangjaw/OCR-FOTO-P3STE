import { NextRequest } from "next/server";
import { subscribeLogs, getPipelineState } from "@/lib/pipeline-runner";

export const dynamic = "force-dynamic";

export async function GET(_req: NextRequest) {
  let unsubscribe: (() => void) | null = null;

  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();

      // Send current status
      const state = getPipelineState();
      controller.enqueue(
        encoder.encode(
          `data: ${JSON.stringify({
            type: "status",
            is_running: state.is_running,
            step: state.current_step,
          })}\n\n`
        )
      );

      // Send last 60 log lines
      for (const line of state.recent_logs) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ type: "log", line })}\n\n`)
        );
      }

      // Subscribe to real-time events
      unsubscribe = subscribeLogs((msg) => {
        try {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(msg)}\n\n`)
          );
        } catch {
          // Stream closed by client
        }
      });
    },
    cancel() {
      if (unsubscribe) {
        unsubscribe();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
