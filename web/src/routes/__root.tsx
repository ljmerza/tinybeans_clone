import { createRootRoute, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import QueryDevtools from '@/integrations/tanstack-query/devtools'
import AuthStoreDevtools from '@/modules/login/devtools'

function RootComponent() {
  return (
    <>
      <Outlet />
      <TanStackRouterDevtools plugins={[QueryDevtools, AuthStoreDevtools]} />
    </>
  )
}

export const Route = createRootRoute({
  component: RootComponent,
})
