import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatCard } from '@/components/features/stat-card'
import { FileText } from 'lucide-react'

describe('StatCard', () => {
  it('renders title and value correctly', () => {
    render(
      <StatCard
        title="Total Documents"
        value={42}
        icon={FileText}
      />
    )

    expect(screen.getByText('Total Documents')).toBeDefined()
    expect(screen.getByText('42')).toBeDefined()
  })

  it('renders description when provided', () => {
    render(
      <StatCard
        title="Total Documents"
        value={42}
        description="Last 30 days"
      />
    )

    expect(screen.getByText('Last 30 days')).toBeDefined()
  })

  it('renders trend indicator when provided', () => {
    render(
      <StatCard
        title="Total Documents"
        value={42}
        trend={{ value: 12, label: 'vs last month' }}
      />
    )

    expect(screen.getByText('+12%')).toBeDefined()
    expect(screen.getByText('vs last month')).toBeDefined()
  })
})
