import {
  Bar,
  BarChart,
  LabelList,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from 'recharts'

import { CHART_FONT_SIZE, chartColorsFor } from '@/lib/chartTheme'
import { useTheme } from '@/hooks/useTheme'

export interface CommunitySizeDatum {
  label: string
  size: number
}

export interface CommunitySizeChartProps {
  data: CommunitySizeDatum[]
  height: number
  onBarClick: () => void
}

/**
 * Horizontal bar chart of community sizes. Loaded lazily so Recharts stays out
 * of the initial bundle.
 */
export function CommunitySizeChart({
  data,
  height,
  onBarClick,
}: CommunitySizeChartProps) {
  const { theme } = useTheme()
  const colors = chartColorsFor(theme)

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 0, right: 40, bottom: 0, left: 0 }}
      >
        <XAxis type="number" hide domain={[0, 'dataMax']} />
        <YAxis
          type="category"
          dataKey="label"
          // Wide enough that "Community <n>" stays on a single line.
          width={104}
          axisLine={false}
          tickLine={false}
          tick={{ fill: colors.axis, fontSize: CHART_FONT_SIZE }}
        />
        <Bar
          dataKey="size"
          fill={colors.accent}
          radius={[0, 2, 2, 0]}
          maxBarSize={14}
          isAnimationActive={false}
          className="cursor-pointer"
          onClick={onBarClick}
        >
          <LabelList
            dataKey="size"
            position="right"
            fill={colors.label}
            fontSize={CHART_FONT_SIZE}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
