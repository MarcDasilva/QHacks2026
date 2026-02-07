"use client"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar"
import { createClient } from "@/lib/supabase/client"
import type { User } from "@supabase/supabase-js"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

function mapSupabaseUser(user: User): { name: string; email: string; avatar: string } {
  const name =
    user.user_metadata?.full_name ??
    user.user_metadata?.name ??
    user.email?.split("@")[0] ??
    "User"
  const email = user.email ?? ""
  const avatar = user.user_metadata?.avatar_url ?? user.user_metadata?.picture ?? ""
  return { name, email, avatar }
}

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      setLoading(false)
      if (!session?.user) {
        router.replace("/")
      }
    })
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      if (!session?.user) {
        router.replace("/")
      }
    })
    return () => subscription.unsubscribe()
  }, [router])

  const handleLogout = async () => {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.replace("/")
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    )
  }

  if (!user) {
    return null
  }

  const sidebarUser = mapSupabaseUser(user)

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" user={sidebarUser} onLogout={handleLogout} />
      <SidebarInset>
        <SiteHeader />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-1 gap-4 overflow-hidden px-4 py-4 md:px-6 md:py-6">
              <div className="min-w-0 flex-1 rounded-xl bg-zinc-200 dark:bg-zinc-800" />
              <div className="w-80 shrink-0 rounded-xl bg-zinc-200 dark:bg-zinc-800 md:w-96" />
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
