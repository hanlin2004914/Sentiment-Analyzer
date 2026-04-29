"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { TooltipProps } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TimeWindowTabs } from "@/components/TimeWindowTabs";
import type {
  EvidenceItem,
  PricePoint,
  PriceSeriesSource,
  TimeWindow
} from "@/lib/types";
import { formatDateTime, formatProbability } from "@/lib/utils";

const sentimentColor = {
  positive: "#059669",
  negative: "#e11d48",
  neutral: "#64748b"
};

type ChartDatum = {
  time: number;
  timestamp: string;
  yesProbability: number;
  volume?: number;
};

function nearestPricePoint(
  evidence: EvidenceItem,
  priceSeries: PricePoint[]
): PricePoint | undefined {
  const eventTime = new Date(evidence.timestamp).getTime();
  return priceSeries.reduce<PricePoint | undefined>((nearest, point) => {
    if (!nearest) return point;
    const currentDistance = Math.abs(
      new Date(point.timestamp).getTime() - eventTime
    );
    const nearestDistance = Math.abs(
      new Date(nearest.timestamp).getTime() - eventTime
    );
    return currentDistance < nearestDistance ? point : nearest;
  }, undefined);
}

function ChartTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload as ChartDatum | undefined;

  return (
    <div className="rounded-md border bg-white p-3 shadow-sm">
      <p className="text-xs font-medium text-muted-foreground">
        {formatDateTime(point?.timestamp ?? new Date(label ?? 0).toISOString())}
      </p>
      <p className="mt-1 text-sm font-semibold text-foreground">
        YES probability: {formatProbability((payload[0].value ?? 0) / 100)}
      </p>
      {point?.volume ? (
        <p className="text-xs text-muted-foreground">
          Interval volume: ${point.volume.toLocaleString()}
        </p>
      ) : null}
    </div>
  );
}

function AnnotationLabel({
  viewBox,
  item,
  index
}: {
  viewBox?: { x?: number; y?: number };
  item: EvidenceItem;
  index: number;
}) {
  const x = viewBox?.x ?? 0;
  const y = viewBox?.y ?? 0;
  const color = sentimentColor[item.sentimentForYes];

  return (
    <g transform={`translate(${x}, ${y + 8})`}>
      <title>
        {item.title} | {item.sentimentForYes} for YES
      </title>
      <circle r="9" fill="white" stroke={color} strokeWidth="1.5" />
      <text
        textAnchor="middle"
        dominantBaseline="central"
        fill={color}
        fontSize="10"
        fontWeight="700"
      >
        {index + 1}
      </text>
    </g>
  );
}

export function PriceMovementChart({
  priceSeries,
  evidenceItems,
  priceSeriesSource,
  selectedTimeWindow,
  onTimeWindowChange
}: {
  priceSeries: PricePoint[];
  evidenceItems: EvidenceItem[];
  priceSeriesSource: PriceSeriesSource;
  selectedTimeWindow: TimeWindow;
  onTimeWindowChange: (timeWindow: TimeWindow) => void;
}) {
  const chartData: ChartDatum[] = priceSeries.map((point) => ({
    time: new Date(point.timestamp).getTime(),
    timestamp: point.timestamp,
    yesProbability: point.yesPrice * 100,
    volume: point.volume
  }));

  const annotationPoints = evidenceItems
    .map((item) => {
      const point = nearestPricePoint(item, priceSeries);
      if (!point) return null;
      return {
        item,
        time: new Date(item.timestamp).getTime(),
        yesProbability: point.yesPrice * 100
      };
    })
    .filter(Boolean) as Array<{
    item: EvidenceItem;
    time: number;
    yesProbability: number;
  }>;

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>YES Price / Implied Probability</CardTitle>
            <Badge
              variant={priceSeriesSource === "clob-history" ? "positive" : "amber"}
            >
              {priceSeriesSource === "clob-history"
                ? "CLOB history"
                : "derived demo series"}
            </Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Vertical annotations mark retrieved news timestamps at the nearest
            available price point.
          </p>
        </div>
        <TimeWindowTabs
          selected={selectedTimeWindow}
          onChange={onTimeWindowChange}
        />
      </CardHeader>
      <CardContent>
        <div className="h-[360px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 18, right: 26, bottom: 12, left: 0 }}
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis
                dataKey="time"
                type="number"
                domain={["dataMin", "dataMax"]}
                tickFormatter={(value) =>
                  formatDateTime(new Date(value).toISOString())
                }
                tickMargin={10}
                minTickGap={32}
              />
              <YAxis
                domain={[0, 100]}
                tickFormatter={(value) => `${value}%`}
                width={44}
              />
              <Tooltip content={<ChartTooltip />} />
              {evidenceItems.map((item, index) => (
                <ReferenceLine
                  key={item.id}
                  x={new Date(item.timestamp).getTime()}
                  stroke={sentimentColor[item.sentimentForYes]}
                  strokeDasharray="4 4"
                  strokeOpacity={0.75}
                  label={(props: { viewBox?: { x?: number; y?: number } }) => (
                    <AnnotationLabel item={item} index={index} {...props} />
                  )}
                />
              ))}
              {annotationPoints.map(({ item, time, yesProbability }) => (
                <ReferenceDot
                  key={`${item.id}-dot`}
                  x={time}
                  y={yesProbability}
                  r={4}
                  fill={sentimentColor[item.sentimentForYes]}
                  stroke="white"
                  strokeWidth={2}
                />
              ))}
              <Line
                type="monotone"
                dataKey="yesProbability"
                stroke="#1d4ed8"
                strokeWidth={2.5}
                dot={priceSeriesSource === "derived-demo"}
                activeDot={{ r: 5, stroke: "#1d4ed8", strokeWidth: 2 }}
                name="YES probability"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
