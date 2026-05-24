import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/api/client'
import { useAuth } from './useAuth'

export type PermissionState = 'default' | 'granted' | 'denied' | 'unsupported'

export interface NotificationChannel {
  id: number
  label: string
  apprise_url: string
  enabled: boolean
  created_at: string
}

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw     = atob(base64)
  const arr     = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i)
  return arr.buffer
}

async function registerSW(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) return null
  try {
    return await navigator.serviceWorker.register('/sw.js')
  } catch {
    return null
  }
}

async function getVapidKey(): Promise<string> {
  const { data } = await api.get('/notifications/vapid-public-key')
  return data.public_key
}

export function useNotifications() {
  const { isAuthenticated } = useAuth()
  const qc = useQueryClient()

  const [permission, setPermission] = useState<PermissionState>(
    typeof Notification !== 'undefined' ? Notification.permission as PermissionState : 'unsupported'
  )
  const [pushSubscribed, setPushSubscribed] = useState(false)

  // Register SW on mount
  useEffect(() => {
    if (!isAuthenticated) return
    registerSW().then((reg) => {
      if (!reg) return
      reg.pushManager.getSubscription().then((sub) => {
        setPushSubscribed(!!sub)
      })
    })
  }, [isAuthenticated])

  // Channels query
  const { data: channels = [], isLoading: channelsLoading } = useQuery<NotificationChannel[]>({
    queryKey: ['notification-channels'],
    queryFn: async () => {
      const { data } = await api.get('/notifications/channels')
      return data.channels ?? []
    },
    enabled: isAuthenticated,
  })

  // Enable browser push
  const enablePush = useMutation({
    mutationFn: async () => {
      const reg = await registerSW()
      if (!reg) throw new Error('Service workers not supported')

      const permission = await Notification.requestPermission()
      if (permission !== 'granted') throw new Error('Permission denied')
      setPermission('granted')

      const vapidKey = await getVapidKey()
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey),
      })

      const subJson = sub.toJSON()
      await api.post('/notifications/push/subscribe', {
        endpoint: subJson.endpoint,
        keys: subJson.keys,
      })

      setPushSubscribed(true)
      return sub
    },
  })

  // Disable browser push
  const disablePush = useMutation({
    mutationFn: async () => {
      const reg = await navigator.serviceWorker?.getRegistration('/sw.js')
      const sub = await reg?.pushManager.getSubscription()
      if (sub) {
        await api.delete('/notifications/push/unsubscribe', { data: { endpoint: sub.endpoint } })
        await sub.unsubscribe()
      }
      setPushSubscribed(false)
    },
  })

  // Add channel
  const addChannel = useMutation({
    mutationFn: (payload: { label: string; apprise_url: string }) =>
      api.post('/notifications/channels', payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notification-channels'] }),
  })

  // Toggle channel
  const toggleChannel = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      api.patch(`/notifications/channels/${id}`, { enabled }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notification-channels'] }),
  })

  // Delete channel
  const deleteChannel = useMutation({
    mutationFn: (id: number) => api.delete(`/notifications/channels/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notification-channels'] }),
  })

  return {
    permission,
    pushSubscribed,
    channels,
    channelsLoading,
    enablePush,
    disablePush,
    addChannel,
    toggleChannel,
    deleteChannel,
  }
}
