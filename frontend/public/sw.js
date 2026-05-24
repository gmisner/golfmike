// GolfMike service worker — handles background push notifications

self.addEventListener('push', (event) => {
  let data = { title: 'GolfMike', body: 'Flight update', url: '/' }
  try {
    data = event.data ? event.data.json() : data
  } catch (_) {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body:    data.body,
      icon:    '/favicon.svg',
      badge:   '/favicon.svg',
      tag:     data.url,           // collapses duplicate notifications
      renotify: true,
      data:    { url: data.url },
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url)
          return client.focus()
        }
      }
      return clients.openWindow(url)
    })
  )
})
