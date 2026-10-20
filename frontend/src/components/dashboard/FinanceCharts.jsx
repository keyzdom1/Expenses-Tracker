import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { formatMoney } from '../../lib/format'

const CHART_COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
  'var(--chart-6)',
  'var(--chart-7)',
  'var(--chart-8)',
]

const TOOLTIP_STYLE = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  color: 'var(--text)',
  fontSize: 12,
}

export function TrendChart({ data, currency, decimalPlaces }) {
  const compact = new Intl.NumberFormat(undefined, {
    notation: 'compact',
    maximumFractionDigits: 1,
  })

  return (
    <div className="h-64 w-full" role="img" aria-label="Income and spending by month">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--border)' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value) => compact.format(value / 10 ** decimalPlaces)}
          />
          <Tooltip
            cursor={{ fill: 'var(--surface-raised)' }}
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, name) => [
              formatMoney(value, currency, decimalPlaces),
              name === 'income_minor' ? 'Income' : 'Spending',
            ]}
          />
          <Bar dataKey="income_minor" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="spending_minor" fill="var(--chart-5)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function CategoryChart({ data, currency, decimalPlaces }) {
  return (
    <div className="grid gap-4 sm:grid-cols-[minmax(0,10rem)_minmax(0,1fr)] sm:items-center">
      <div className="h-40 w-full" role="img" aria-label="Spending by category">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="spent_minor"
              nameKey="name"
              innerRadius={44}
              outerRadius={68}
              paddingAngle={2}
              stroke="var(--surface)"
            >
              {data.map((entry, index) => (
                <Cell key={entry.category_id ?? entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(value) => formatMoney(value, currency, decimalPlaces)}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <ul className="space-y-2">
        {data.slice(0, 6).map((slice, index) => (
          <li key={slice.category_id ?? slice.name} className="flex items-center gap-2 text-xs">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
              aria-hidden="true"
            />
            <span className="min-w-0 flex-1 truncate text-text">{slice.name}</span>
            <span className="shrink-0 text-text-muted">{slice.share}%</span>
            <span className="w-24 shrink-0 text-right font-medium text-text">
              {formatMoney(slice.spent_minor, currency, decimalPlaces)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
