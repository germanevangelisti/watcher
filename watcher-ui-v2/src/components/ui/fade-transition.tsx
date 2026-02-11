import { useEffect, useState } from "react"
import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface FadeTransitionProps {
  children: ReactNode
  isLoading: boolean
  skeleton?: ReactNode
  duration?: number
  className?: string
}

export function FadeTransition({
  children,
  isLoading,
  skeleton,
  duration = 300,
  className,
}: FadeTransitionProps) {
  const [shouldShowSkeleton, setShouldShowSkeleton] = useState(isLoading)
  const [isVisible, setIsVisible] = useState(!isLoading)

  useEffect(() => {
    if (isLoading) {
      // Fade out current content
      setIsVisible(false)
      // Show skeleton after fade out
      const timer = setTimeout(() => {
        setShouldShowSkeleton(true)
      }, duration)
      return () => clearTimeout(timer)
    } else {
      // Hide skeleton
      setShouldShowSkeleton(false)
      // Fade in new content
      const timer = setTimeout(() => {
        setIsVisible(true)
      }, 50)
      return () => clearTimeout(timer)
    }
  }, [isLoading, duration])

  return (
    <div className={cn("relative", className)}>
      {/* Skeleton overlay */}
      {shouldShowSkeleton && skeleton && (
        <div
          className="animate-in fade-in"
          style={{ animationDuration: `${duration}ms` }}
        >
          {skeleton}
        </div>
      )}
      
      {/* Actual content */}
      {!shouldShowSkeleton && (
        <div
          className={cn(
            "transition-opacity",
            isVisible ? "opacity-100" : "opacity-0"
          )}
          style={{ transitionDuration: `${duration}ms` }}
        >
          {children}
        </div>
      )}
    </div>
  )
}
