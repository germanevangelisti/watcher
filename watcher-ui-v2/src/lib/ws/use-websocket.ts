/**
 * Reusable WebSocket hook for real-time event subscriptions.
 * Connects to ws://localhost:8001/ws and subscribes to specified event types.
 */

import { useEffect, useRef, useState, useCallback } from "react"

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8001/api/v1/ws"

export interface WebSocketEvent {
  type: string
  event_type: string
  data: Record<string, unknown>
  source: string
  timestamp: string
}

interface UseWebSocketOptions {
  eventTypes: string[]
  enabled?: boolean
  onEvent?: (event: WebSocketEvent) => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

interface UseWebSocketReturn {
  lastEvent: WebSocketEvent | null
  events: WebSocketEvent[]
  isConnected: boolean
  reconnecting: boolean
  clearEvents: () => void
}

export function useWebSocket({
  eventTypes,
  enabled = true,
  onEvent,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)
  const [lastEvent, setLastEvent] = useState<WebSocketEvent | null>(null)
  const [events, setEvents] = useState<WebSocketEvent[]>([])

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onEventRef = useRef(onEvent)
  const eventTypesRef = useRef(eventTypes)

  // Keep refs up to date
  useEffect(() => {
    onEventRef.current = onEvent
  }, [onEvent])

  useEffect(() => {
    eventTypesRef.current = eventTypes
  }, [eventTypes])

  const clearEvents = useCallback(() => {
    setEvents([])
    setLastEvent(null)
  }, [])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        setReconnecting(false)
        reconnectAttempts.current = 0

        // Subscribe to requested event types
        if (eventTypesRef.current.length > 0) {
          ws.send(
            JSON.stringify({
              action: "subscribe",
              event_types: eventTypesRef.current,
            })
          )
        }
      }

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as WebSocketEvent
          
          // Only handle actual events (not connection messages)
          if (data.type === "event" && data.event_type) {
            setLastEvent(data)
            setEvents((prev) => {
              // Keep max 200 events in memory
              const next = [...prev, data]
              return next.length > 200 ? next.slice(-200) : next
            })
            onEventRef.current?.(data)
          }
        } catch {
          // Ignore non-JSON messages
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        wsRef.current = null

        // Auto-reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          setReconnecting(true)
          reconnectAttempts.current += 1
          reconnectTimeout.current = setTimeout(connect, reconnectInterval)
        } else {
          setReconnecting(false)
        }
      }

      ws.onerror = () => {
        // Error handling is done in onclose
        ws.close()
      }
    } catch {
      // Connection failed, will retry in onclose
    }
  }, [reconnectInterval, maxReconnectAttempts])

  useEffect(() => {
    if (!enabled) {
      wsRef.current?.close()
      wsRef.current = null
      setIsConnected(false)
      return
    }

    connect()

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current)
      }
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [enabled, connect])

  // Re-subscribe when event types change
  useEffect(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN && eventTypes.length > 0) {
      wsRef.current.send(
        JSON.stringify({
          action: "subscribe",
          event_types: eventTypes,
        })
      )
    }
  }, [eventTypes])

  return {
    lastEvent,
    events,
    isConnected,
    reconnecting,
    clearEvents,
  }
}
