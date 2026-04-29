import { NextResponse } from "next/server";
import { searchNewsEvidence } from "@/lib/news";
import type { NewsSearchInput } from "@/lib/types";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as Partial<NewsSearchInput>;

    if (!body.marketQuestion || !body.yesOutcome || !body.noOutcome) {
      return NextResponse.json(
        {
          error:
            "marketQuestion, yesOutcome, and noOutcome are required to search evidence."
        },
        { status: 400 }
      );
    }

    const evidenceItems = await searchNewsEvidence({
      marketQuestion: body.marketQuestion,
      category: body.category ?? "Other",
      keywords: body.keywords ?? [],
      startDate: body.startDate,
      endDate: body.endDate,
      yesOutcome: body.yesOutcome,
      noOutcome: body.noOutcome
    });

    return NextResponse.json({ evidenceItems });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Unable to search news."
      },
      { status: 502 }
    );
  }
}
